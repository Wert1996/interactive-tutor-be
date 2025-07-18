from datetime import datetime
import json
from app.models.course import CommandType
from app.models.dashboard import ActivityStatus, Dashboard, ParentStats
from app.models.session import Event, Session
from app.dao.db import Db
from app.resources.openai import create_response
from app.utils.prompts import session_stats_system_prompt


class DashboardBuilder:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db = Db.get_instance()
        self.user = self.db.get_user(self.user_id)
        self.sessions = self.db.get_sessions_by_user_id(self.user_id)

    async def build_session_stats(self):
        event_logs = self.session.event_logs
        if len(event_logs) > 0 and event_logs[-1].type == "dashboard_built":
            return
        day_wise_time_spent = {}
        last_ping_timestamp = None
        course = self.db.get_course(self.session.course_id)
        phases_completed = 0
        questions_answered = 0
        questions_correctly_answered = 0
        questions_asked = 0
        for event in event_logs:
            if event.type == "ping":
                day = event.timestamp.split("T")[0]
                if day not in day_wise_time_spent:
                    day_wise_time_spent[day] = 0
                else:
                    if last_ping_timestamp is not None:
                        if event.timestamp - last_ping_timestamp <= 40:
                            day_wise_time_spent[day] += event.timestamp - last_ping_timestamp
                last_ping_timestamp = event.timestamp
            elif event.type == "next_phase":
                phases_completed += 1
            elif event.type == "student_interaction":
                if event.data.get("interaction", {}).get("type") in ["mcq_question", "binary_choice_question"]:
                    questions_answered += 1
                    if event.data.get("interaction", {}).get("correct", False):
                        questions_correctly_answered += 1
                elif event.data.get("interaction", {}).get("type") == "student_speech":
                    speech_interactions_count += 1
            elif event.type == "execute_command":
                if event.data.get("command", {}).get("command_type") in [CommandType.MCQ_QUESTION, CommandType.BINARY_CHOICE_QUESTION]:
                    questions_asked += 1

        self.session.session_stats.questions_answered = questions_answered
        self.session.session_stats.questions_asked = questions_asked
        self.session.session_stats.time_spent_per_day = day_wise_time_spent
        self.session.session_stats.speech_interactions_count = speech_interactions_count
        self.session.session_stats.session_time = sum(day_wise_time_spent.values())
        self.session.session_stats.mastery_score = questions_correctly_answered / questions_asked
        self.session.session_stats.completion = phases_completed / course.stats.total_phases

        # Use LLM to get subjective stats
        system_prompt = session_stats_system_prompt
        user_prompt = "Give the scores by analyzing the session in this chat"
        response = await create_response(instructions=system_prompt, message=user_prompt)
        response = json.loads(response.output_text)
        self.session.session_stats.engagement_score = response.get("engagement_score")
        self.session.session_stats.comprehension_score = response.get("comprehension_score")
        self.session.session_stats.skill_stats.retention_score = response.get("retention_score")
        self.session.session_stats.skill_stats.critical_thinking_score = response.get("critical_thinking_score")
        self.session.session_stats.skill_stats.problem_solving_score = response.get("problem_solving_score")
        self.session.session_stats.skill_stats.creativity_score = response.get("creativity_score")
        self.session.session_stats.skill_stats.communication_score = response.get("communication_score")
        self.session.session_stats.skill_stats.self_awareness_score = response.get("self_awareness_score")
        self.session.session_stats.skill_stats.social_skills_score = response.get("social_skills_score")
        self.session.session_stats.skill_stats.emotional_intelligence_score = response.get("emotional_intelligence_score")
        self.session.session_stats.skill_stats.curiosity_score = response.get("curiosity_score")
        self.session.session_stats.learning_insights = response.get("learning_insights")
        self.session.session_stats.parent_recommendations = response.get("parent_recommendations")

        # Resetting this so that the system instructions are set again when the user starts learning
        self.session.system_instructions = None
        # Clean up event logs
        self.session.event_logs = [event for event in self.session.event_logs if event.type == "dashboard_built"]
        self.session.event_logs.append(Event(type="dashboard_built", data={}, timestamp=datetime.now().isoformat()))
        self.db.update_session_in_memory(self.session.id, self.session.model_dump())

    def build_user_stats(self):
        # Get the total time spent in the learning sessions
        """
        User stats:
            streak: int
            total_learning_time: float
            overall_completion_rate: float
            total_lessons_started: int
            average_session_time: float
            learning_insights: Optional[str] = None
            skill_stats_history: Optional[List[SkillStats]] = None
            skill_stats_aggregate: Optional[SkillStats] = None
        """
        self.user.user_stats.total_learning_time = sum([session.session_stats.session_time for session in self.sessions])
        self.user.user_stats.overall_completion_rate = sum([session.session_stats.completion for session in self.sessions]) / len(self.sessions)
        self.user.user_stats.total_lessons_started = len(self.sessions)
        self.user.user_stats.average_session_time = total_time_spent / len(self.sessions)
        self.user.user_stats.skill_stats_history = [session.session_stats.skill_stats for session in self.sessions]
        # List of session insights
        self.user.user_stats.learning_insights = [session.session_stats.learning_insights for session in self.sessions] 
        # Average of all the sessions' skill stats
        self.user.user_stats.skill_stats_aggregate = {
            "mastery_score": sum([session.session_stats.skill_stats.mastery_score for session in self.sessions]) / len(self.sessions),
            "retention_score": sum([session.session_stats.skill_stats.retention_score for session in self.sessions]) / len(self.sessions),
            "critical_thinking_score": sum([session.session_stats.skill_stats.critical_thinking_score for session in self.sessions]) / len(self.sessions),
            "problem_solving_score": sum([session.session_stats.skill_stats.problem_solving_score for session in self.sessions]) / len(self.sessions),
            "creativity_score": sum([session.session_stats.skill_stats.creativity_score for session in self.sessions]) / len(self.sessions),
            "communication_score": sum([session.session_stats.skill_stats.communication_score for session in self.sessions]) / len(self.sessions),
            "self_awareness_score": sum([session.session_stats.skill_stats.self_awareness_score for session in self.sessions]) / len(self.sessions),
            "social_skills_score": sum([session.session_stats.skill_stats.social_skills_score for session in self.sessions]) / len(self.sessions),
            "emotional_intelligence_score": sum([session.session_stats.skill_stats.emotional_intelligence_score for session in self.sessions]) / len(self.sessions),
            "curiosity_score": sum([session.session_stats.skill_stats.curiosity_score for session in self.sessions]) / len(self.sessions),
        }


    def build_parent_stats(self):
        """
        Parent stats:
            recommendation_completion: float
            recommended_activities: List[ParentActivity]    
        """
        parent_stats = ParentStats()
        parent_recommendations = []
        for session in self.sessions:
            parent_recommendations.extend(session.session_stats.parent_recommendations)
        parent_stats.recommendation_completion = sum([parent_recommendation.activity_status == ActivityStatus.COMPLETED for parent_recommendation in parent_recommendations]) / len(parent_recommendations)
        parent_stats.recommended_activities = parent_recommendations
        return parent_stats


    async def build_dashboard(self):
        # Should lock the session before building the dashboard, and unlock it after the dashboard is built.
        # This is because the system instructions are changed for building the dashbord. Build the dashboard only when the user is inactive.
        for session in self.sessions:
            await self.build_session_stats(session)
        self.build_user_stats()
        parent_stats = self.build_parent_stats()
        self.db.update_user(self.user_id, self.user.model_dump())
        dashboard = Dashboard(
            user_id=self.user_id,
            user_stats=self.user.user_stats,
            session_stats=[session.session_stats for session in self.sessions],
            parent_stats=parent_stats
        )
        self.db.update_dashboard(self.user_id, dashboard.model_dump())

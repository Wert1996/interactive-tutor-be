from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel


class SkillStats(BaseModel):
    mastery_score: float
    retention_score: Optional[float] = None
    critical_thinking_score: Optional[float] = None
    problem_solving_score: Optional[float] = None
    creativity_score: Optional[float] = None
    communication_score: Optional[float] = None
    self_awareness_score: Optional[float] = None
    social_skills_score: Optional[float] = None
    emotional_intelligence_score: Optional[float] = None
    curiosity_score: Optional[float] = None


class UserStats(BaseModel):
    streak: int
    total_learning_time: float
    overall_completion_rate: float
    total_lessons_started: int
    average_session_time: float
    learning_insights: Optional[List[str]] = None
    skill_stats_history: Optional[List[SkillStats]] = None
    skill_stats_aggregate: Optional[SkillStats] = None


class ActivityStatus(str, Enum):
    COMPLETED = "completed"
    NOT_COMPLETED = "not_completed"


class ParentActivity(BaseModel):
    activity_name: str
    activity_description: str
    activity_type: str
    activity_duration: float
    objectives: List[str]
    activity_status: ActivityStatus

class SessionStats(BaseModel):
    session_id: str
    date: Optional[datetime] = None
    completion: Optional[float] = None
    # Total time spent in the learning session in seconds. (this is not one instance of learning, but all the time spent in the session, which is a course and user mapping)
    session_time: Optional[float] = None
    time_spent_per_day: Optional[Dict[str, float]] = None
    questions_answered: Optional[int] = None
    questions_asked: Optional[int] = None
    speech_interactions_count: Optional[int] = None
    # Below are more subjective stats.
    mastery_score: Optional[float] = None
    engagement_score: Optional[float] = None
    comprehension_score: Optional[float] = None
    topic_wise_mastery: Optional[Dict[str, float]] = None
    skill_stats: Optional[SkillStats] = None
    learning_insights: Optional[str] = None
    parent_recommendations: Optional[List[ParentActivity]] = None


class ParentStats(BaseModel):
    recommendation_completion: float
    recommended_activities: List[ParentActivity]    


class Dashboard(BaseModel):
    user_id: str
    user_stats: UserStats
    session_stats: List[SessionStats]
    parent_stats: ParentStats

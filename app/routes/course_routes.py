from fastapi import APIRouter, HTTPException

from app.dao.db import Db
from app.models.course import Course, CourseTopic, Module

router = APIRouter(prefix="/api/courses", tags=["courses"])

@router.get("/{course_id}", response_model=Course)
async def get_course(course_id: str):
    """
    Get a course by its ID.
    
    Args:
        course_id: The ID of the course to retrieve
        
    Returns:
        Course: The course object
    """
    db = Db.get_instance()
    
    if course_id not in db.courses:
        raise HTTPException(
            status_code=404,
            detail=f"Course with id '{course_id}' not found"
        )
    
    return Course(**db.courses[course_id])


@router.get("/")
async def list_courses():
    """
    List all courses.
    
    Returns:
        Dict: All courses data
        {
            "id": str,
            "title": str,
            "description": str,
            "category": str,
            "estimatedDuration": str,
            "topics": [
                {
                    "title": str,
                    "description": str,
                    "modules": [
                        {
                            "title": str,
                            "description": str,
                        }
                    ]
                }
            ]
        }
    """
    db = Db.get_instance()
    courses = db.courses 
    # No need for phases. Will have to copy the course data to a new object.
    course_projections = []
    for course in courses.values():
        course_projection = Course(
            id=course.get("id"),
            title=course.get("title"),
            description=course.get("description"),
            category=course.get("category"),
            estimatedDuration=course.get("estimatedDuration"),
            topics=[]
        )
        topics = course.get("topics", [])
        for topic in topics:
            topic_projection = CourseTopic(
                title=topic.get("title"),
                description=topic.get("description"),
                modules=[]
            )
            modules = topic.get("modules", [])
            for module in modules:
                module_projection = Module(
                    title=module.get("title"),
                    description=module.get("description"),
                )
                topic_projection.modules.append(module_projection)
            course_projection.topics.append(topic_projection)
        course_projections.append(course_projection)
    return course_projections
    
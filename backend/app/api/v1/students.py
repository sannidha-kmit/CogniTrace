from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_role
from app.db.mongodb import get_database
from app.schemas.course import StudentListItemResponse

router = APIRouter()


@router.get("/my-year", response_model=List[StudentListItemResponse])
async def get_students_for_teacher_year(
    current_teacher: dict = Depends(require_role(["teacher"]))
):
    """
    Retrieve students belonging strictly to the authenticated teacher's target academic year.
    Sorted in natural alphanumeric order by Roll Number.
    """
    database = await get_database()
    teacher_year = current_teacher["year"]

    cursor = database.students.find({"year": teacher_year}).sort("roll_number", 1)
    students = await cursor.to_list(length=1000)

    return [
        StudentListItemResponse(
            id=str(s["_id"]),
            roll_number=s["roll_number"],
            name=s["name"],
            year=s["year"]
        )
        for s in students
    ]

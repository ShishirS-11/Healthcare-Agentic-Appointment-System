
import json

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError

from langchain_core.tools import tool

from database.connection import SessionLocal
from database.models import Department, Doctor


@tool
def find_departments_and_doctors(
    department_name: str = "",
    doctor_name: str = "",
) -> str:
    """
    Find active medical departments and registered doctors.

    Optionally filter results by department name or doctor name.

    Returns department names, doctor names, specializations,
    and qualifications. Does not expose private patient information.
    """

    try:
        with SessionLocal() as db:

            statement = (
                select(Department, Doctor)
                .outerjoin(
                    Doctor,
                    Doctor.department_id == Department.id,
                )
                .where(
                    Department.is_active.is_(True),
                    or_(
                        Doctor.is_active.is_(True),
                        Doctor.id.is_(None),
                    ),
                )
                .order_by(
                    Department.name.asc(),
                    Doctor.full_name.asc(),
                )
            )

            if department_name.strip():
                statement = statement.where(
                    Department.name.ilike(
                        f"%{department_name.strip()}%"
                    )
                )

            if doctor_name.strip():
                statement = statement.where(
                    Doctor.full_name.ilike(
                        f"%{doctor_name.strip()}%"
                    )
                )

            results = db.execute(statement).all()

            departments = {}

            for department, doctor in results:

                if department.id not in departments:
                    departments[department.id] = {
                        "department_id": department.id,
                        "department_name": department.name,
                        "description": department.description,
                        "doctors": [],
                    }

                if doctor is not None:
                    departments[department.id]["doctors"].append(
                        {
                            "doctor_id": doctor.id,
                            "doctor_name": doctor.full_name,
                            "specialization": doctor.specialization,
                            "qualification": doctor.qualification,
                        }
                    )

            response = {
                "success": True,
                "total_departments": len(departments),
                "total_doctors": sum(
                    len(item["doctors"])
                    for item in departments.values()
                ),
                "departments": list(departments.values()),
            }

            return json.dumps(response, indent=2)

    except SQLAlchemyError:
        return json.dumps(
            {
                "success": False,
                "error": "Unable to retrieve departments and doctors.",
            }
        )

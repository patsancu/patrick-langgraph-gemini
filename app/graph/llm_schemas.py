from pydantic import BaseModel, Field
from typing import List

class UseCase(BaseModel):
    title: str = Field(description="The title of the use case ticket")
    description: str = Field(description="The detailed description of what needs to be implemented for this use case")

class POExtraction(BaseModel):
    use_cases: List[UseCase] = Field(description="A list of use cases extracted from the user's initial request")

class DevTask(BaseModel):
    title: str = Field(description="The title of the developer task")
    description: str = Field(description="Detailed technical requirements for this task")
    type: str = Field(description="The type of task: must be exactly one of 'frontend', 'backend', or 'devops'")

class DevLeadExtraction(BaseModel):
    tasks: List[DevTask] = Field(description="A list of technical tasks required to fulfill the use cases")

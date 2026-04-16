from pydantic import BaseModel


class JobData(BaseModel):
    job_id: int
    dataset_name: str
    dataset_id: int
    status: str


class TrainedModelData(BaseModel):
    job_id: int
    model_name: str
    model_version: str

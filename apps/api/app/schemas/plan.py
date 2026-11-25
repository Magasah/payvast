from pydantic import BaseModel, ConfigDict


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name_tg: str
    name_ru: str
    price_dirams: int
    duration_days: int
    device_limit: int

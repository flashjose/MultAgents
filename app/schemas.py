from pydantic import BaseModel, Field


class PluginLoadRequest(BaseModel):
    path: str = Field(description="Absolute or relative path to a plugin .py file")


class PluginActionResponse(BaseModel):
    status: str
    platform: str | None = None
    platforms: list[str] | None = None
    message: str | None = None

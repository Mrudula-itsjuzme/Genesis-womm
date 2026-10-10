from pydantic import BaseModel, ConfigDict, Field


class ProposalIngestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: str = Field(description="UUID of the proposal record in Core API")
    event_id: str = Field(description="UUID of the event the proposal belongs to")
    club_id: str = Field(description="UUID of the club organizing the event")
    revision: int = Field(default=1, ge=1, description="Proposal revision sequence number")
    presigned_url: str = Field(description="Temporary 15-minute presigned download URL for PDF")
    title: str = Field(description="Title of the event proposal")
    submitted_by: str | None = None
    approved_by: str | None = None


class ProposalIngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: str
    event_id: str
    chunks_ingested: int = Field(ge=0)
    collection: str = "proposals"
    status: str = "success"


class ProposalDeletePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(description="UUID of the event whose proposal chunks should be deleted")


class ProposalDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: str
    event_id: str
    chunks_deleted: int = Field(ge=0)
    status: str

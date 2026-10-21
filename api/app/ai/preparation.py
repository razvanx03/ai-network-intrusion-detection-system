"""Model-independent normalization; no feature vector or model assumptions."""
from collections.abc import Sequence
from pydantic import BaseModel, ConfigDict
from app.models.connection import Connection
from app.schemas.connection import ZeekLogItem

PREPARATION_VERSION = "zeek-connection-v1"


class PreparedConnection(BaseModel):
    model_config = ConfigDict(frozen=True)
    connection_id: int
    record: ZeekLogItem


def prepare_connections(connections: Sequence[Connection]) -> tuple[PreparedConnection, ...]:
    return tuple(
        PreparedConnection(
            connection_id=connection.id,
            record=ZeekLogItem.model_validate({
                name: getattr(connection, name) for name in ZeekLogItem.model_fields
            }),
        ) for connection in connections
    )

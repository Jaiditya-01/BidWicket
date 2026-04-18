from typing import List, Optional

from pydantic import BaseModel


class SearchResult(BaseModel):
    entity: str
    id: str
    title: str
    subtitle: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]

from fastapi import Form, UploadFile, File
from pydantic import BaseModel
from typing import Optional

class StyleTransformRequest:
    def __init__(
        self,
        image: UploadFile = File(...),
        strength: Optional[float] = Form(None),
    ):
        self.image = image
        self.strength = strength

    @classmethod
    def as_form(
        cls,
        image: UploadFile = File(...),
        strength: Optional[float] = Form(None),
    ):
        return cls(image=image, strength=strength) 
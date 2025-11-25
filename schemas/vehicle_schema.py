from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class VehicleSchema(BaseModel):
    type: Optional[str] = Field(None, description="Type of vehicle (e.g., Car, Motorcycle)")
    brand: Optional[str] = Field(None, description="Vehicle brand/manufacturer")
    model: Optional[str] = Field(None, description="Vehicle model")
    year: Optional[int] = Field(None, description="Year of manufacture")
    transmission: Optional[str] = Field(None, description="Transmission type (e.g., Automatic, Manual)")
    licensePlate: Optional[str] = Field(None, alias="licensePlate", description="Vehicle license plate number")
    chassisNumber: Optional[str] = Field(None, alias="chassisNumber", description="Vehicle chassis/VIN number")
    engineNumber: Optional[str] = Field(None, alias="engineNumber", description="Engine number")
    color: Optional[str] = Field(None, description="Vehicle color")

    class Config:
        populate_by_name = True


class DriverSchema(BaseModel):
    driverLicenseId: Optional[str] = Field(None, alias="driverLicenseId", description="Driver's license ID number")
    name: Optional[str] = Field(None, description="Driver's first name")
    surname: Optional[str] = Field(None, description="Driver's surname/last name")
    dateOfBirth: Optional[str] = Field(None, alias="dateOfBirth", description="Date of birth in YYYY-MM-DD format")
    countryOfBirth: Optional[str] = Field(None, alias="countryOfBirth", description="Country of birth")
    validFrom: Optional[str] = Field(None, alias="validFrom", description="License valid from date in YYYY-MM-DD format")
    validTo: Optional[str] = Field(None, alias="validTo", description="License valid to date in YYYY-MM-DD format")
    issuingAuthority: Optional[str] = Field(None, alias="issuingAuthority", description="License issuing authority")
    address: Optional[str] = Field(None, description="Driver's address")
    addressMatchesDVLA: Optional[bool] = Field(None, alias="addressMatchesDVLA", description="Whether address matches DVLA records")

    class Config:
        populate_by_name = True


class VehicleDriverSchema(BaseModel):
    vehicle: VehicleSchema = Field(..., description="Vehicle information")
    driver: DriverSchema = Field(..., description="Driver information")

    class Config:
        populate_by_name = True

from pydantic import BaseModel, Field

class HierarchicalConfig(BaseModel):
    min_customer_history: int = Field(default=3, description="Minimum events needed for customer mode")
    min_merchant_history: int = Field(default=50, description="Minimum events needed for merchant mode")
    min_population_history: int = Field(default=100, description="Minimum events needed for population mode")
    default_probability: float = Field(default=0.1, description="Probability returned in default mode")

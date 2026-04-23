from dataclasses import dataclass, asdict
from typing import Optional, Dict


@dataclass
class UserProfile:
    user_id: int

    monthly_budget: float = 0.0
    income: Optional[float] = None

    risk_tolerance: str = "medium"
    investment_style: str = "balanced"

    age: Optional[int] = None
    horizon_years: Optional[int] = None

    is_active: bool = True

    auto_invest_enabled: bool = False
    last_auto_invest: Optional[str] = None



USER_STORE: Dict[int, UserProfile] = {}



def create_user_profile(user_id: int) -> UserProfile:
    profile = UserProfile(user_id=user_id)
    USER_STORE[user_id] = profile
    return profile


def get_user_profile(user_id: int) -> Optional[UserProfile]:
    return USER_STORE.get(user_id)


def update_user_profile(user_id: int, **kwargs) -> Optional[UserProfile]:
    profile = USER_STORE.get(user_id)

    if not profile:
        return None

    for key, value in kwargs.items():
        if hasattr(profile, key):
            setattr(profile, key, value)

    return profile


def delete_user_profile(user_id: int):
    if user_id in USER_STORE:
        del USER_STORE[user_id]



def validate_profile(profile: UserProfile) -> Dict:
    issues = []

    if profile.monthly_budget <= 0:
        issues.append("Monthly budget not set")

    if profile.risk_tolerance not in ["low", "medium", "high"]:
        issues.append("Invalid risk tolerance")

    if profile.age and (profile.age < 10 or profile.age > 100):
        issues.append("Unrealistic age")

    return {
        "valid": len(issues) == 0,
        "issues": issues
    }



def get_effective_monthly_budget(profile: UserProfile, total_value=None):

    if profile.monthly_budget > 0:
        return profile.monthly_budget

    if profile.income:

        if profile.risk_tolerance == "low":
            pct = 0.1
        elif profile.risk_tolerance == "high":
            pct = 0.3
        else:
            pct = 0.2

        return round(profile.income * pct, 2)

    if total_value:
        return round(total_value * 0.03, 2)

    return 100

def get_risk_multiplier(profile: UserProfile):

    mapping = {
        "low": 0.8,
        "medium": 1.0,
        "high": 1.2
    }

    return mapping.get(profile.risk_tolerance, 1.0)


def to_dict(profile: UserProfile) -> Dict:
    return asdict(profile)
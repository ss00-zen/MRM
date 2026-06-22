def check_drift_threshold(drift):
    return drift > 0.15


def regulatory_policy():
    return {
        "policy": "SR11-7",
        "max_drift": 0.15
    }
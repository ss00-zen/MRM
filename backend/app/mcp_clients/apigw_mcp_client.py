class APIGWMCPClient:
    async def get_live_drift_signal(self, model_id: str):
        return {
            "model_id": model_id,
            "psi": 0.18,
            "source": "stubbed_apigw"
        }
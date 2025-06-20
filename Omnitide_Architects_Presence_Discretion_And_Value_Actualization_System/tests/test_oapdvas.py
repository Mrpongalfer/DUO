from fastapi.testclient import TestClient
from Omnitide_Architects_Presence_Discretion_And_Value_Actualization_System.main_oapdvas_service import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "OAPDVAS Genesis Actualizer Online"

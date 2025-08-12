from app import create_app

def test_hello_world():
    app = create_app()
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    assert b'Hello, World!' in response.data
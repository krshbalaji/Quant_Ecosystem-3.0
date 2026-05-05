from google.cloud import secretmanager

def get_secret(secret_id, project_id="quant-ecosystem-23037"):
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(name=name)
        return response.payload.data.decode("UTF-8")

    except Exception as e:
        print(f"[SecretManager] fallback triggered: {e}")
        return None
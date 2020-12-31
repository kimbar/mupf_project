import mupf


app = mupf.App()
client = mupf.client.Client(app, app.get_unique_client_id())
client.summoned()

print(f"sefe dunders = {client._safe_dunders_feature}")

r = mupf._remote.RemoteObj(2, client)

print(r)
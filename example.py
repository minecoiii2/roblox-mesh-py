import robloxmesh
import re
import requests

EXAMPLE_ACCESSORY_ID = 16728087416

def deliver_asset(asset_id: int):
    delivery = requests.get('https://assetdelivery.roblox.com/v1/assetId/' + asset_id).json()
    return requests.get(delivery["location"]).content

# Converts Accessory ID into MeshId
rbxm_file = deliver_asset(EXAMPLE_ACCESSORY_ID).decode("ISO-8859-1") # Converts to string ig
matches = re.compile(r'rbxassetid://(.*?)PROP', re.DOTALL).findall(rbxm_file)
mesh_id = matches[0]

# Opens Accessory
robloxmesh_file = deliver_asset(mesh_id)
file = robloxmesh.RobloxMesh(robloxmesh_file)
file.export("./export.obj")
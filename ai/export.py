"""Package the selected model with its deployment manifest, without logs or secrets."""
import json
from zipfile import ZipFile, ZIP_DEFLATED

from ai.acquire import ROOT, WORK, digest


def main() -> None:
    deployment = ROOT / "api/app/ai/deployment.json"
    manifest = json.loads(deployment.read_text())
    artifact = (deployment.parent / manifest["artifact"]).resolve()
    if not artifact.is_relative_to((deployment.parent / "models").resolve()):
        raise ValueError("Invalid selected artifact path")
    if digest(artifact) != manifest["sha256"]:
        raise ValueError("Selected artifact failed checksum verification")
    output = WORK / "export/selected-ai-model.zip"
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(artifact, "api/app/ai/models/selected.joblib")
        archive.write(deployment, "api/app/ai/deployment.json")
        archive.write(ROOT / "api/requirements.txt", "api/requirements.txt")
    print(output)


if __name__ == "__main__":
    main()

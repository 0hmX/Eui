#!/usr/bin/env python3
"""Eui Chatterbox JSON-lines worker protocol v1.

The worker intentionally owns every Chatterbox/torch import and model instance.
The TypeScript process sends narration as JSON on stdin, never as shell source.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

PROTOCOL = "eui.chatterbox"
VERSION = 1
_models: dict[str, Any] = {}


def _device(requested: str) -> str:
    import torch

    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _model(device: str) -> Any:
    if device not in _models:
        from chatterbox.tts import ChatterboxTTS

        _models[device] = ChatterboxTTS.from_pretrained(device=device)
    return _models[device]


def _synthesize(params: dict[str, Any]) -> dict[str, Any]:
    # Imports and model loading stay in this worker, and only happen on a real request.
    import torch
    import torchaudio

    text = params.get("text")
    output_path = params.get("outputPath")
    seed = params.get("seed")
    requested_device = params.get("device", "auto")
    reference = params.get("voiceReferencePath")
    options = params.get("options", {})
    if not isinstance(text, str) or not text.strip():
        raise ValueError("params.text must be a non-empty string")
    if not isinstance(output_path, str) or not output_path:
        raise ValueError("params.outputPath must be a non-empty string")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("params.seed must be an integer")
    if requested_device not in {"auto", "cpu", "cuda", "mps"}:
        raise ValueError("params.device is invalid")
    if reference is not None and not isinstance(reference, str):
        raise ValueError("params.voiceReferencePath must be a string or null")
    if not isinstance(options, dict):
        raise ValueError("params.options must be an object")

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    device = _device(requested_device)
    model = _model(device)
    kwargs = dict(options)
    if reference:
        kwargs["audio_prompt_path"] = reference
    audio = model.generate(text, **kwargs)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    try:
        torchaudio.save(str(temporary), audio, model.sr, format="wav")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {"sampleRate": int(model.sr)}


def _handle(message: Any) -> dict[str, Any]:
    if not isinstance(message, dict):
        raise ValueError("request must be an object")
    if message.get("protocol") != PROTOCOL or message.get("version") != VERSION:
        raise ValueError("unsupported Chatterbox worker protocol")
    request_id = message.get("id")
    if not isinstance(request_id, str) or not request_id:
        raise ValueError("request id must be a non-empty string")
    if message.get("method") != "synthesize":
        raise ValueError("unsupported worker method")
    params = message.get("params")
    if not isinstance(params, dict):
        raise ValueError("params must be an object")
    return {
        "protocol": PROTOCOL,
        "version": VERSION,
        "id": request_id,
        "ok": True,
        "result": _synthesize(params),
    }


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        request_id: Any = None
        try:
            message = json.loads(line)
            if isinstance(message, dict):
                request_id = message.get("id")
            response = _handle(message)
        except Exception as error:  # protocol boundary: return a structured failure
            response = {
                "protocol": PROTOCOL,
                "version": VERSION,
                "id": request_id,
                "ok": False,
                "error": {"message": str(error), "type": type(error).__name__},
            }
        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

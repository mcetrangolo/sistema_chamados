import json

from django.http import JsonResponse


def api_success(data=None, status=200, **extra):
    payload = {"success": True, "data": data if data is not None else {}}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def api_error(code, message, status=400, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JsonResponse({"success": False, "error": error}, status=status)


def json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

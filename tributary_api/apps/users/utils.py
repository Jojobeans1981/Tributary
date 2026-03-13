from rest_framework.response import Response


def ok(data):
    return Response({"success": True, "data": data})


def err(code, msg, status=400):
    return Response(
        {"success": False, "error": {"code": code, "message": msg}},
        status=status,
    )

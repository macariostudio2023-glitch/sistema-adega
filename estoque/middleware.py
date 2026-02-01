from django.shortcuts import redirect

class AdminGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # deixa passar a rota que valida a senha
        if path == "/admin-gate-check/":
            return self.get_response(request)

        # libera arquivos estáticos (admin e site) pra não quebrar css/js
        if path.startswith("/static/") or path.startswith("/media/"):
            return self.get_response(request)

        # trava qualquer tentativa de entrar no admin sem ter liberado
        if path.startswith("/admin/"):
            if not request.session.get("admin_gate_ok", False):
                return redirect("/")  # manda pro início (onde fica o botão Admin)

        return self.get_response(request)

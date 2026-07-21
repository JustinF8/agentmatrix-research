#!/usr/bin/env python3
"""
Model Adapter — 因子看板 (agentmatrix-research-因子看板) 消费 Fusion Hub 的适配器。

Fusion Hub 由 model-main/fusion_api.py 提供，统一暴露：
  - 908 因子 IC 数据   (factor_api，挂载在 /factor，需 X-API-Key)
  - 90+ 策略代码清单   (/v1/strategies)
  - 93 策略回测结果     (/v1/strategy-results)

【放置位置】复制到因子看板项目内，例如：
    agentmatrix-research-因子看板/research_core/adapters/model_adapter.py
（adapters 目录不存在则新建，并加 __init__.py）

【用法 A：作为客户端直接调用】
    from model_adapter import ModelAdapter
    adapter = ModelAdapter(base_url="http://127.0.0.1:8799", api_key="<自动生成的Key>")
    factors   = adapter.list_factors(limit=20)
    results   = adapter.list_strategy_results()

【用法 B：在后端注册代理路由（框架无关，自动适配 Flask / FastAPI）】
    # 因子看板后端 backend/factor_lab_api.py（Flask）：
    from research_core.adapters.model_adapter import register_model_routes
    register_model_routes(app, base_url="http://127.0.0.1:8799",
                          api_key=os.getenv("FUSION_HUB_API_KEY"), prefix="/api/model")
    # 之后看板前端可访问 /api/model/factors、/api/model/strategy-results ...
"""
import requests


class ModelAdapter:
    def __init__(self, base_url="http://127.0.0.1:8799", api_key=None, timeout=30):
        self.base = base_url.rstrip("/")
        self.key = api_key
        self.timeout = timeout

    def _headers(self):
        return {"X-API-Key": self.key} if self.key else {}

    # ── 因子 ──
    def list_factors(self, category=None, limit=50):
        params = {"limit": limit}
        if category:
            params["category"] = category
        r = requests.get(f"{self.base}/factor/v1/factors", params=params,
                         headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_factor(self, name):
        r = requests.get(f"{self.base}/factor/v1/factors/{name}",
                         headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def top_factors(self, by="ic_ir", n=20):
        r = requests.get(f"{self.base}/factor/v1/top", params={"by": by, "n": n},
                         headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ── 策略 ──
    def list_strategy_code(self, category=None):
        params = {}
        if category:
            params["category"] = category
        r = requests.get(f"{self.base}/v1/strategies", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def strategy_source(self, sid):
        r = requests.get(f"{self.base}/v1/strategies/{sid}/source", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_strategy_results(self, group=None, limit=100):
        params = {"limit": limit}
        if group:
            params["group"] = group
        r = requests.get(f"{self.base}/v1/strategy-results", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def strategy_result_detail(self, sid):
        r = requests.get(f"{self.base}/v1/strategy-results/{sid}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def overview(self):
        r = requests.get(f"{self.base}/v1/fusion/overview", timeout=self.timeout)
        r.raise_for_status()
        return r.json()


def register_model_routes(app, base_url="http://127.0.0.1:8799",
                          api_key=None, prefix="/api/model"):
    """在因子看板后端上注册 Model 项目（Fusion Hub）代理路由。

    自动适配框架：
      - FastAPI / Starlette 应用（拥有 .get 方法）→ 用 @app.get 注册
      - Flask 应用（无 .get 方法）→ 用 @app.route(..., methods=["GET"]) 注册

    上游 Fusion Hub 不可达时返回 502，不影响看板其余功能。
    """
    adapter = ModelAdapter(base_url=base_url, api_key=api_key)
    # 注意：Flask 2.0+ 也提供了 .get() 装饰器，不能仅靠 hasattr(app, "get") 判断。
    # 这里用类所属模块名区分（无需 import fastapi，避免给纯 Flask 场景强加依赖）。
    is_fastapi = type(app).__module__.startswith("fastapi.")

    if is_fastapi:
        from fastapi import HTTPException

        def _safe(call):
            try:
                return call()
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=502, detail=f"Fusion Hub 不可达: {exc}")

        @app.get(f"{prefix}/factors")
        def _factors(category: str = None, limit: int = 50):
            return _safe(lambda: adapter.list_factors(category=category, limit=limit))

        @app.get(f"{prefix}/factors/{{name}}")
        def _factor(name: str):
            return _safe(lambda: adapter.get_factor(name))

        @app.get(f"{prefix}/top")
        def _top(by: str = "ic_ir", n: int = 20):
            return _safe(lambda: adapter.top_factors(by=by, n=n))

        @app.get(f"{prefix}/strategies")
        def _strategies(category: str = None):
            return _safe(lambda: adapter.list_strategy_code(category=category))

        @app.get(f"{prefix}/strategies/{{sid}}/source")
        def _src(sid: str):
            return _safe(lambda: adapter.strategy_source(sid))

        @app.get(f"{prefix}/strategy-results")
        def _results(group: str = None, limit: int = 100):
            return _safe(lambda: adapter.list_strategy_results(group=group, limit=limit))

        @app.get(f"{prefix}/strategy-results/{{sid}}")
        def _result(sid: str):
            return _safe(lambda: adapter.strategy_result_detail(sid))

        @app.get(f"{prefix}/overview")
        def _overview():
            return _safe(lambda: adapter.overview())

    else:  # Flask
        from flask import jsonify, request

        def _safe(call):
            try:
                return call(), 200
            except Exception as exc:  # noqa: BLE001
                return {"error": f"Fusion Hub 不可达: {exc}", "upstream": "fusion-hub"}, 502

        @app.route(f"{prefix}/factors", methods=["GET"])
        def _model_factors():
            category = request.args.get("category")
            try:
                limit = int(request.args.get("limit", 50))
            except (TypeError, ValueError):
                limit = 50
            data, status = _safe(lambda: adapter.list_factors(category=category, limit=limit))
            return jsonify(data), status

        @app.route(f"{prefix}/factors/<name>", methods=["GET"])
        def _model_factor(name):
            data, status = _safe(lambda: adapter.get_factor(name))
            return jsonify(data), status

        @app.route(f"{prefix}/top", methods=["GET"])
        def _model_top():
            by = request.args.get("by", "ic_ir")
            try:
                n = int(request.args.get("n", 20))
            except (TypeError, ValueError):
                n = 20
            data, status = _safe(lambda: adapter.top_factors(by=by, n=n))
            return jsonify(data), status

        @app.route(f"{prefix}/strategies", methods=["GET"])
        def _model_strategies():
            category = request.args.get("category")
            data, status = _safe(lambda: adapter.list_strategy_code(category=category))
            return jsonify(data), status

        @app.route(f"{prefix}/strategies/<sid>/source", methods=["GET"])
        def _model_strategy_source(sid):
            data, status = _safe(lambda: adapter.strategy_source(sid))
            return jsonify(data), status

        @app.route(f"{prefix}/strategy-results", methods=["GET"])
        def _model_strategy_results():
            group = request.args.get("group")
            try:
                limit = int(request.args.get("limit", 100))
            except (TypeError, ValueError):
                limit = 100
            data, status = _safe(lambda: adapter.list_strategy_results(group=group, limit=limit))
            return jsonify(data), status

        @app.route(f"{prefix}/strategy-results/<sid>", methods=["GET"])
        def _model_strategy_result(sid):
            data, status = _safe(lambda: adapter.strategy_result_detail(sid))
            return jsonify(data), status

        @app.route(f"{prefix}/overview", methods=["GET"])
        def _model_overview():
            data, status = _safe(lambda: adapter.overview())
            return jsonify(data), status

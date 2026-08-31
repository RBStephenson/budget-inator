from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.bill_instances import router as bill_instances_router
from app.api.bills import router as bills_router
from app.api.data import router as data_router
from app.api.health import router as health_router
from app.api.pay_period_actuals import router as pay_period_actuals_router
from app.api.pay_period_overrides import router as pay_period_overrides_router
from app.api.pay_schedule import router as pay_schedule_router
from app.api.reports import router as reports_router
from app.api.schedule import router as schedule_router
from app.config import settings
from app.logging_config import log_request

app = FastAPI(title="Budget-inator API")

app.middleware("http")(log_request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(pay_schedule_router)
app.include_router(bills_router)
app.include_router(schedule_router)
app.include_router(bill_instances_router)
app.include_router(pay_period_overrides_router)
app.include_router(pay_period_actuals_router)
app.include_router(data_router)
app.include_router(reports_router)

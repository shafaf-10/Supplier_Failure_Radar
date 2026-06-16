from app.ml.feature_engineering.helpers import left_merge


def build_master_supplier_table(
    suppliers,
    booking_features=None,
    process_features=None,
    ticketing_features=None,
    session_features=None,
    refund_features=None,
    credit_features=None,
    wallet_features=None,
):
    master = suppliers.copy()

    master = master.rename(
        columns={
            "code": "supplier_code",
            "name": "supplier_name",
        }
    )

    keep_cols = [
        "supplier_code",
        "supplier_name",
        "is_active",
        "health_status",
    ]

    master = master[
        [col for col in keep_cols if col in master.columns]
    ]

    feature_parts = [
        booking_features,
        process_features,
        ticketing_features,
        session_features,
        refund_features,
        credit_features,
        wallet_features,
    ]

    for part in feature_parts:
        master = left_merge(
            master,
            part,
            on="supplier_code",
        )

    return master.fillna(0)
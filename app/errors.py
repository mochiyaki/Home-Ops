class VendorNotConfigured(Exception):
    """Raised when a vendor key is missing and HOMEOPS_MOCK is off."""

    def __init__(self, vendor: str, env_var: str):
        self.vendor = vendor
        self.env_var = env_var
        super().__init__(
            f"{vendor} is not configured. Set {env_var} or HOMEOPS_MOCK=1 "
            "for a labeled demo mock."
        )


class VendorError(Exception):
    """Upstream vendor call failed."""

    def __init__(self, vendor: str, detail: str):
        self.vendor = vendor
        self.detail = detail
        super().__init__(detail)


class DangerBlocked(Exception):
    def __init__(self, detail: str = "Emergency — do not call a vendor."):
        self.detail = detail
        super().__init__(detail)


class CallCapExceeded(Exception):
    def __init__(self):
        self.detail = (
            "HomeOps already placed 3 calls. Ask to try another if you want one more."
        )
        super().__init__(self.detail)

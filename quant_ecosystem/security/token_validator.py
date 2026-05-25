class TokenValidator:

    def validate(
        self,
        token,
    ):
        return token == "QE3_SECURE_TOKEN"


token_validator = TokenValidator()
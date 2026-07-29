from pydantic import BaseModel, HttpUrl


class NasProfile(BaseModel):
    name: str
    adapter: str
    base_url: HttpUrl | None = None
    username: str | None = None
    default_download_dir: str | None = None


class ProfileStore(BaseModel):
    profiles: dict[str, NasProfile]
    default_profile: str | None = None

    def get(self, name: str) -> NasProfile:
        try:
            return self.profiles[name]
        except KeyError as exc:
            raise KeyError(f"Unknown NAS profile: {name}") from exc

    def default(self) -> NasProfile:
        if self.default_profile is None:
            raise KeyError("No default NAS profile configured")
        return self.get(self.default_profile)

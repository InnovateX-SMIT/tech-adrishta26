import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from backend.app.config import settings
from backend.app.models.registry import (
    MemberStatus,
    RegisterMemberRequest,
    RescueMember,
)
from backend.app.storage.json_store import load_json, save_json


class RegistryServiceError(Exception):
    """Base exception for registry service operations."""
    pass


class MemberNotFoundError(RegistryServiceError):
    """Raised when a rescue member cannot be found."""
    pass


class MemberAlreadyRevokedError(RegistryServiceError):
    """Raised when attempting to revoke an already revoked member."""
    pass


class RegistryService:
    """Manages trusted rescue-team registry records and administrative device identifiers.

    Note on Concurrency:
    JSON registry writes are atomic at the file-replacement level, but multi-process
    concurrent registration locking is outside Phase 2.
    """

    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or (settings.data_dir / "registry.json")

    def _load_raw_registry(self) -> Dict[str, Any]:
        """Loads raw JSON registry or initializes a default structure if missing."""
        default_data = {"version": 1, "members": []}
        data = load_json(self.registry_path, default=default_data)
        if not isinstance(data, dict):
            data = default_data
        if "members" not in data or not isinstance(data["members"], list):
            data["members"] = []
        if "version" not in data:
            data["version"] = 1
        return data

    def _save_raw_registry(self, data: Dict[str, Any]) -> None:
        """Persists the registry atomically using safe JSON replacement."""
        save_json(self.registry_path, data)

    def _parse_members(self, raw_members: List[Dict[str, Any]]) -> List[RescueMember]:
        members: List[RescueMember] = []
        for raw in raw_members:
            try:
                members.append(RescueMember(**raw))
            except Exception:
                continue
        return members

    def _generate_next_rescue_id(self, existing_members: List[RescueMember]) -> str:
        """Generates the next unique Rescue ID, handling gaps and never reusing IDs."""
        existing_ids: Set[str] = {m.rescue_id for m in existing_members}
        max_num = 0
        pattern = re.compile(r"^RESQ-(\d+)$")

        for rid in existing_ids:
            match = pattern.match(rid)
            if match:
                try:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    continue

        candidate_num = max_num + 1
        candidate_id = f"RESQ-{candidate_num:03d}"
        while candidate_id in existing_ids:
            candidate_num += 1
            candidate_id = f"RESQ-{candidate_num:03d}"

        return candidate_id

    def _generate_next_device_id(self, existing_members: List[RescueMember]) -> str:
        """Generates the next unique Device ID, handling gaps and never reusing IDs."""
        existing_ids: Set[str] = {m.device_id for m in existing_members}
        max_num = 0
        pattern = re.compile(r"^DEVICE-(\d+)$")

        for did in existing_ids:
            match = pattern.match(did)
            if match:
                try:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    continue

        candidate_num = max_num + 1
        candidate_id = f"DEVICE-{candidate_num:03d}"
        while candidate_id in existing_ids:
            candidate_num += 1
            candidate_id = f"DEVICE-{candidate_num:03d}"

        return candidate_id

    def get_all_members(self) -> List[RescueMember]:
        """Returns all registered members (active and revoked), preserving historical order."""
        raw_data = self._load_raw_registry()
        return self._parse_members(raw_data.get("members", []))

    def get_member_by_rescue_id(self, rescue_id: str) -> Optional[RescueMember]:
        """Looks up a member by exact Rescue ID."""
        members = self.get_all_members()
        for member in members:
            if member.rescue_id == rescue_id:
                return member
        return None

    def get_member_by_device_id(self, device_id: str) -> Optional[RescueMember]:
        """Looks up a member by exact Device ID."""
        members = self.get_all_members()
        for member in members:
            if member.device_id == device_id:
                return member
        return None

    def is_member_active(self, rescue_id: str) -> bool:
        """Returns True if member exists and has active status, False otherwise."""
        member = self.get_member_by_rescue_id(rescue_id)
        if member is None:
            return False
        return member.status == MemberStatus.ACTIVE

    def register_member(self, request: RegisterMemberRequest) -> RescueMember:
        """Registers a new rescue team member with auto-generated unique IDs and active status."""
        raw_data = self._load_raw_registry()
        members = self._parse_members(raw_data.get("members", []))

        # Generate unique non-colliding IDs
        rescue_id = self._generate_next_rescue_id(members)
        device_id = self._generate_next_device_id(members)

        now_utc = datetime.now(timezone.utc).isoformat()

        # Strict Phase 2 rule: public-key fields must be server-controlled and null
        new_member = RescueMember(
            rescue_id=rescue_id,
            name=request.name,
            team=request.team,
            role=request.role,
            device_id=device_id,
            signing_public_key=None,
            encryption_public_key=None,
            status=MemberStatus.ACTIVE,
            created_at=now_utc,
            revoked_at=None,
        )

        # Store in raw data structure
        raw_data["members"].append(new_member.model_dump())
        self._save_raw_registry(raw_data)

        return new_member

    def revoke_member(self, rescue_id: str) -> RescueMember:
        """Revokes an active member, recording revoked_at while preserving the historical record."""
        raw_data = self._load_raw_registry()
        raw_members = raw_data.get("members", [])

        target_index = -1
        for idx, item in enumerate(raw_members):
            if item.get("rescue_id") == rescue_id:
                target_index = idx
                break

        if target_index == -1:
            raise MemberNotFoundError(f"Member with Rescue ID '{rescue_id}' not found.")

        current_member = RescueMember(**raw_members[target_index])
        if current_member.status == MemberStatus.REVOKED:
            raise MemberAlreadyRevokedError(f"Member '{rescue_id}' is already revoked.")

        now_utc = datetime.now(timezone.utc).isoformat()
        current_member.status = MemberStatus.REVOKED
        current_member.revoked_at = now_utc

        raw_members[target_index] = current_member.model_dump()
        raw_data["members"] = raw_members
        self._save_raw_registry(raw_data)

        return current_member


# Default service instance using settings.data_dir
registry_service = RegistryService()

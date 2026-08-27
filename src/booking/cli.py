"""Management CLI: docker compose exec api python -m booking.cli <command>."""

import argparse
import asyncio

from booking.core.config import get_settings
from booking.db.engine import get_session_factory
from booking.models.users import Role, RoleCode
from booking.repositories.users import RoleRepository, SystemUserRepository
from booking.services import security
from booking.worker import run_worker


async def create_staff(email: str, password: str, role_code: RoleCode) -> None:
    factory = get_session_factory()
    async with factory() as session:
        roles = RoleRepository(session)
        role = await roles.get_by_code(role_code)
        if role is None:
            role = Role(code=role_code, name=role_code.value.title())
            session.add(role)
            await session.flush()
        users = SystemUserRepository(session)
        existing = await users.get_by_email(email)
        if existing is not None:
            raise SystemExit(f"user {email} already exists")
        user = await users.create(
            email=email,
            password_hash=security.hash_password(password),
            role_id=role.id,
        )
        await session.commit()
        print(f"created system user {user.email} (role={role.code.value})")


def main() -> None:
    parser = argparse.ArgumentParser(prog="booking.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    staff = sub.add_parser("create-staff", help="create a system user")
    staff.add_argument("email")
    staff.add_argument("password")
    staff.add_argument("--role", default="admin", choices=[r.value for r in RoleCode])
    worker = sub.add_parser(
        "cleanup-worker", help="run the expired-reservation cleanup worker"
    )
    worker.add_argument("--interval", type=int, default=60, help="seconds between runs")
    args = parser.parse_args()
    get_settings()
    if args.command == "create-staff":
        asyncio.run(create_staff(args.email, args.password, RoleCode(args.role)))
    elif args.command == "cleanup-worker":
        asyncio.run(run_worker(args.interval))


if __name__ == "__main__":
    main()

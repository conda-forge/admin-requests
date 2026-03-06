# /// script
# dependencies = ["py-rattler>=0.22,<0.23"]
# ///
import asyncio
import sys
from itertools import chain
from rattler import Gateway, Platform


def search(*specs):
    async def inner():
        return await Gateway().query(
            sources=["conda-forge"],
            platforms=Platform.all(),
            specs=specs,
            recursive=False,
        )

    return asyncio.run(inner())


if not sys.argv[1:]:
    sys.exit("Pass at least one matchspec to query")


print(*[f"- {r.subdir}/{r.file_name}" for r in chain(*search(*sys.argv[1:]))], sep="\n")

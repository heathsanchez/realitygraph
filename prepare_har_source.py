from realitygraph.har_grouped import HAR_URL, source_digest

size, digest = source_digest(".cache/grouped-real")
print("REALITYGRAPH / HAR SOURCE-ONLY ACQUISITION")
print(f"url={HAR_URL}")
print(f"bytes={size}")
print(f"sha256={digest}")
print("NO_LABEL_EVALUATION=1")

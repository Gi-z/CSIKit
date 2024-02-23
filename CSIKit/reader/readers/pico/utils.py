def parse_with_relevant_parser(version_map: dict, version: int, data: bytes, segment_name: str):
    if version in version_map:
        return version_map[version](data)
    else:
        latest_version = max(version_map.keys())
        print(f"Parser for version {version} of {segment_name} is not available.")
        print(f"Defaulting to parser for latest version {latest_version} of {segment_name} instead.")
        return version_map[latest_version](data)

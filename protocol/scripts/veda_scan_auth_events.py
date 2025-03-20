"""
Blockchain Event Scanner for Authority Contract

This script scans blockchain events for a given BoringVault and its Authority contract, specifically tracking:
1. UserRoleUpdated - Events that assign/remove roles to/from user addresses
2. RoleCapabilityUpdated - Events that grant/revoke permissions for roles to call specific functions on target contracts
3. OwnershipTransferred - Events that track changes in contract ownership

The script:
- Fetches vault info (symbol and authority address) from blockchain
- Gets contract deployment and last activity blocks from Etherscan
- Fetches historical events from the blockchain
- Caches results by contract address and chain ID to minimize RPC calls
- Resolves contract names via Etherscan API with local fallback
- Maps function signatures to human-readable names
- Generates a markdown table showing:
    - Which addresses have which roles
    - What functions each role can call
    - Which contracts (targets) they can interact with
    - Current owner of the authority contract

Supports multiple chains:
- Ethereum Mainnet (1)
- Polygon (137)
- Sonic (146)

Output is saved to protocol/data/{vault_name}-auth-{contract_address}-{chain_id}.md for easy viewing and tracking of permission changes.
"""

import csv
import json
import logging
import os
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import requests
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_web3(chain_id: int) -> Web3:
    """
    Get Web3 instance for given chain ID
    Returns: Web3 instance
    """
    rpc_url = os.getenv(f"RPC_{chain_id}")
    if not rpc_url:
        raise ValueError(f"Missing env variable RPC_{chain_id}")

    return Web3(Web3.HTTPProvider(rpc_url))


def get_vault_info(vault_address: str, chain_id: int) -> tuple[str, str]:
    """
    Get vault symbol, authority address and owner address from vault contract
    Returns: (vault_symbol, authority_address)
    """
    # Load vault ABI
    with open("protocol/scripts/abi/boring_vault.json") as f:
        vault_abi = json.load(f)

    w3 = get_web3(chain_id)
    vault_contract = w3.eth.contract(
        address=Web3.to_checksum_address(vault_address), abi=vault_abi
    )

    with w3.batch_requests() as batch:
        batch.add(vault_contract.functions.symbol())
        batch.add(vault_contract.functions.authority())
        batch.add(vault_contract.functions.owner())
        results = batch.execute()
        if len(results) != 3:
            raise ValueError("Expected 3 results from batch requests")
        symbol = results[0]
        authority = results[1]
        owner = results[2]
        if owner != "0x0000000000000000000000000000000000000000":
            raise ValueError(
                "BoringVault owner is not 0x0000000000000000000000000000000000000000"
            )
        return symbol, authority


def get_authority_owner(authority_address: str, chain_id: int) -> str:
    """
    Get owner address from authority contract
    Returns: owner address
    """
    # Load vault ABI
    with open("protocol/scripts/abi/authority.json") as f:
        authority_abi = json.load(f)

    w3 = get_web3(chain_id)
    authority_contract = w3.eth.contract(
        address=Web3.to_checksum_address(authority_address),
        abi=authority_abi,
    )
    owner = authority_contract.functions.owner().call()
    return owner


def scan_events(
    contract_address: str,
    chain_id: int,
    abi_path: str,
    event_names: List[str],
    from_block: int,
    to_block: Optional[int] = "latest",
    batch_size: int = 10000,
) -> Dict[str, List[dict]]:
    """
    Scan blockchain for specific events with proper error handling and batching
    """
    w3 = get_web3(chain_id)
    # NOTE: tenderly dont' have restriction on batch size
    # batch_size = to_block - from_block

    # Load ABI
    with open(abi_path) as f:
        abi = json.load(f)

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_address), abi=abi
    )

    all_events = {event_name: [] for event_name in event_names}
    current_block = from_block
    end_block = w3.eth.block_number if to_block == "latest" else to_block

    while current_block < end_block:
        chunk_end = min(current_block + batch_size, end_block)

        try:
            # Get logs for each event type
            for event_name in event_names:
                event = getattr(contract.events, event_name)
                logs = event.get_logs(from_block=current_block, to_block=chunk_end)
                all_events[event_name].extend(logs)

            logger.info(f"Scanned blocks {current_block} to {chunk_end}")
            current_block = chunk_end + 1

        except Exception as e:
            logger.error(f"Error in batch {current_block}-{chunk_end}: {e}")
            # Reduce batch size on error
            batch_size = batch_size // 2
            if batch_size < 100:
                raise Exception("Batch size too small, something is wrong")
            continue

    return all_events


def process_events_to_table(
    events: Dict[str, List[dict]], function_signatures: Dict[str, str], chain_id: int
) -> Tuple[List[dict], str]:
    """Process events into table format, handling both cached and fresh events"""
    # Store role -> addresses mapping
    role_addresses: Dict[int, Set[str]] = defaultdict(set)
    # Store role -> {target -> {function_sig}} mapping
    role_permissions: Dict[int, Dict[str, Set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    table_rows = []
    owner_address = None

    # First pass: build mappings
    for event_name, logs in events.items():
        for log in logs:
            args = dict(log.args) if hasattr(log, "args") else log["args"]

            if event_name == "UserRoleUpdated":
                role = (
                    int(args["role"]) if isinstance(args["role"], str) else args["role"]
                )
                if args["enabled"]:
                    role_addresses[role].add(args["user"])
                else:
                    role_addresses[role].discard(args["user"])

            elif event_name == "RoleCapabilityUpdated":
                role = (
                    int(args["role"]) if isinstance(args["role"], str) else args["role"]
                )
                # Ensure function signature always starts with 0x
                if isinstance(args["functionSig"], bytes):
                    sig = "0x" + args["functionSig"].hex()
                else:
                    # If it's a string, ensure it starts with 0x
                    sig = (
                        args["functionSig"]
                        if args["functionSig"].startswith("0x")
                        else "0x" + args["functionSig"]
                    )
                if args["enabled"]:
                    role_permissions[role][args["target"]].add(sig)
                else:
                    role_permissions[role][args["target"]].discard(sig)

            # elif event_name == "OwnershipTransferred":
            #     owner_address = args["newOwner"]

    # Second pass: generate table rows
    for role, addresses in role_addresses.items():
        for target, sigs in role_permissions[role].items():
            for sig in sigs:
                name = function_signatures.get(sig, "Unknown Function")
                for user_address in addresses:
                    row = {
                        "Role ID": role,
                        "User Name": get_contract_name(user_address, chain_id),
                        "Target Name": get_contract_name(target, chain_id),
                        "Function Names": name,
                        "Function Signatures": sig,  # This will always have 0x prefix now
                        "User Address": user_address,
                        "Target Address": target,
                    }
                    table_rows.append(row)

    return table_rows, owner_address


def get_etherscan_config(chain_id: int) -> tuple[str, str]:
    """
    Get Etherscan API URL and API key for given chain ID
    Returns: (api_url, api_key)
    """
    if chain_id == 1:
        api_url = "https://api.etherscan.io/api"
        api_key = os.getenv("ETHERSCAN_API_KEY")
    elif chain_id == 137:
        api_url = "https://api.polygonscan.com/api"
        api_key = os.getenv("POLYGONSCAN_API_KEY")
    elif chain_id == 146:
        api_url = "https://api.sonicscan.org/api"
        api_key = os.getenv("SONICSCAN_API_KEY")
    else:
        raise ValueError(f"Unsupported chain_id: {chain_id}")

    if api_key is None:
        raise ValueError(f"Missing API key for chain_id: {chain_id}")

    return api_url, api_key


@lru_cache(maxsize=100)
def get_contract_name_from_etherscan(address: str, chain_id: int) -> str:
    """
    Get contract name from Etherscan API by searching source code for known contract names
    """
    # Known contract names we're looking for
    KNOWN_CONTRACT_NAMES = {
        "BoringVault": ["BoringVault"],
        "Teller": [
            "TellerWithMultiAssetSupport",
            "Teller",
            "TellerWithRemediation",
            "LayerZeroTeller",
        ],
        "BoringOnChainQueue": ["BoringOnChainQueue", "OnChainQueue"],
        "Manager": ["ManagerWithMerkleVerification"],
        "BoringSolver": ["BoringSolver", "Solver"],
        "Pauser": ["Pauser"],
        "Accountant": ["AccountantWithFixedRate", "AccountantWithRateProviders"],
        "Timelock": ["TimelockController"],
        "Queue": [
            "WithdrawQueue",
            "BoringOnChainQueue",
            "BoringOnChainQueueWithTracking",
        ],
        "Multisig": [
            "Proxy",
            "SafeProxy",
            "GnosisSafeProxy",
        ],  # example where proxy is multisig: https://etherscan.io/address/0x0792dCb7080466e4Bbc678Bdb873FE7D969832B8#code
    }

    api_url, etherscan_api_key = get_etherscan_config(chain_id)

    try:
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": etherscan_api_key,
        }

        response = requests.get(api_url, params=params)
        data = response.json()

        if (
            data.get("message") == "NOTOK"
            and "rate limit" in data.get("result", "").lower()
        ):
            logger.warning("Rate limit hit, waiting 1 second...")
            time.sleep(1)
            return get_contract_name_from_etherscan(address, chain_id)

        if data["status"] == "1" and data["result"][0]:
            # First check if ContractName is provided directly by Etherscan
            contract_name = data["result"][0].get("ContractName")
            if contract_name and len(contract_name) > 0:
                # Check if this contract name maps to one of our known types
                for display_name, possible_names in KNOWN_CONTRACT_NAMES.items():
                    if contract_name in possible_names:
                        logger.info(
                            f"Found known contract {display_name} ({contract_name}) at {address}"
                        )
                        return display_name
                # If we have a name from Etherscan but it's not in our mapping, log and return it
                logger.info(
                    f"Found contract {contract_name} at {address} (not in known mappings)"
                )
                return contract_name

            source_code = data["result"][0].get("SourceCode", "")
            logger.info(f"Source code: {source_code}")
            if len(source_code) < 10:
                return "EOA"

            # Fallback to finding the contract name in the source code
            for display_name, possible_names in KNOWN_CONTRACT_NAMES.items():
                for contract_name in possible_names:
                    # Look for "contract ContractName {" pattern
                    if f"contract {contract_name}" in source_code:
                        logger.info(
                            f"Found contract {display_name} at {address} using fallback method"
                        )
                        return display_name

        elif data["status"] == "0":
            logger.warning(
                f"Etherscan API error: {data.get('message', 'Unknown error')}"
            )

    except Exception as e:
        logger.warning(
            f"Error fetching contract name from Etherscan for {address}: {e}"
        )

    return "Unknown"


def get_contract_name(address: str, chain_id: int) -> str:
    """
    Get contract name from local mapping or Etherscan
    """
    # Local mapping for known contracts
    contract_names = {
        "0x358CFACf00d0B4634849821BB3d1965b472c776a": "Teller",
        "0x3754480db8b3E607fbE125697EB496a44A1Be720": "BoringOnChainQueue",
        # ... etc
    }

    # Try local mapping first
    if address in contract_names:
        return contract_names[address]

    # If not in local mapping, try Etherscan
    return get_contract_name_from_etherscan(address, chain_id)


def load_function_signatures(
    csv_path: str = "protocol/scripts/veda_function_signatures.csv",
) -> Dict[str, str]:
    """
    Load function signatures from CSV file
    Returns: Dict[signature -> function_name]
    """
    signatures = {}
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            signatures[row["function_sig"]] = row["function_name"]
    return signatures


def get_function_info(sig: str, signatures: Dict[str, str]) -> Tuple[str, str]:
    """
    Returns both signature and name
    Returns: (signature, function_name)
    """
    # Remove '0x' if present for consistency
    clean_sig = sig.replace("0x", "")
    return f"0x{clean_sig}", signatures.get(clean_sig, clean_sig)


def save_events_to_file(events: dict, filename: str = "cached_events.json"):
    """Save events to a JSON file in a consistent format"""
    serializable_events = {}
    for event_name, logs in events.items():
        serializable_events[event_name] = [
            {
                "blockNumber": (
                    log.blockNumber
                    if hasattr(log, "blockNumber")
                    else log["blockNumber"]
                ),
                "transactionHash": (
                    log.transactionHash.hex()
                    if hasattr(log, "transactionHash")
                    else log["transactionHash"]
                ),
                "args": {
                    k: v.hex() if isinstance(v, bytes) else v
                    for k, v in (
                        dict(log.args) if hasattr(log, "args") else log["args"]
                    ).items()
                },
            }
            for log in logs
        ]

    with open(filename, "w") as f:
        json.dump(serializable_events, f, indent=2)


def load_events_from_file(filename: str = "cached_events.json") -> dict:
    """Load events from a JSON file"""
    if not Path(filename).exists():
        return None

    with open(filename, "r") as f:
        return json.load(f)


def get_events(
    contract_address: str,
    chain_id: int,
    abi_path: str,
    event_names: List[str],
    from_block: int,
    to_block: Optional[int] = "latest",
    use_cache: bool = True,
) -> Dict[str, List[dict]]:
    """Get events either from cache or by scanning blockchain"""
    cache_file = f"cached_events_{contract_address}_{chain_id}.json"
    # Try to load from cache if enabled
    if use_cache:
        cached_events = load_events_from_file(cache_file)
        if cached_events is not None:
            logger.info("Using cached events")
            return cached_events

    # If no cache or cache disabled, scan blockchain
    logger.info("Scanning blockchain for events")
    events = scan_events(
        contract_address=contract_address,
        chain_id=chain_id,
        abi_path=abi_path,
        event_names=event_names,
        from_block=from_block,
        to_block=to_block,
    )

    # Save to cache if enabled
    if use_cache:
        save_events_to_file(events, cache_file)

    return events


def save_markdown_table(
    contract_address: str,
    table_rows: List[dict],
    boring_vault_address: str,
    chain_id: int,
    vault_name: str,
    owner: str,
):
    """Save the roles and permissions data as a markdown table"""
    filename = f"protocol/data/{vault_name}-auth-{contract_address}-{chain_id}.md"
    with open(filename, "w") as f:
        # Write table header
        f.write(
            f"# Authorization Roles and Permissions for Authority contract {contract_address}\n\n"
        )
        f.write(
            f"BoringVault {vault_name} address: {boring_vault_address} on chain {chain_id}\n\n"
        )
        if owner:
            f.write(f"Last owner of the authority contract is: {owner}\n\n")
        f.write(
            "| User Name | Target Name | Function Names | Function Signatures | User Address | Target Address |\n"
        )
        f.write(
            "|-----------|-------------|----------------|-------------------|--------------|----------------|\n"
        )

        # Write table rows
        for row in table_rows:
            f.write(
                f"| {row['User Name']} | {row['Target Name']} | {row['Function Names']} | "
                f"{row['Function Signatures']} | {row['User Address']} | {row['Target Address']} |\n"
            )

    logger.info(f"Table saved to {filename}")


def get_contract_deployment_info(
    contract_address: str, chain_id: int
) -> tuple[int, int]:
    """Get contract creation and last activity block using Etherscan API"""
    api_url, etherscan_api_key = get_etherscan_config(chain_id)

    try:
        # Get contract creation info
        params = {
            "module": "contract",
            "action": "getcontractcreation",
            "contractaddresses": contract_address,
            "apikey": etherscan_api_key,
        }

        response = requests.get(api_url, params=params)
        data = response.json()

        if data.get("status") == "1" and data.get("result"):
            # Get the creation transaction hash
            tx_hash = data["result"][0]["txHash"]
            logger.info(f"Creation tx hash: {tx_hash}")

            # Get transaction info to get block number
            params = {
                "module": "proxy",
                "action": "eth_getTransactionByHash",
                "txhash": tx_hash,
                "apikey": etherscan_api_key,
            }

            response = requests.get(api_url, params=params)
            tx_data = response.json()

            if tx_data.get(
                "result"
            ):  # Changed from checking status to checking result directly
                creation_block = int(
                    tx_data["result"]["blockNumber"], 16
                )  # Convert hex to int
                logger.info(
                    f"Contract {contract_address} was created at block {creation_block}"
                )

                # Get latest block
                params = {
                    "module": "proxy",
                    "action": "eth_blockNumber",
                    "apikey": etherscan_api_key,
                }

                response = requests.get(api_url, params=params)
                block_data = response.json()

                if block_data.get("result"):
                    latest_block = int(block_data["result"], 16)  # Convert hex to int
                    logger.info(f"Current latest block is {latest_block}")
                    return creation_block, latest_block
                else:
                    logger.warning("Could not get latest block")
                    return creation_block, 0

        logger.warning(
            f"Could not get contract creation info: {data.get('message', 'Unknown error')}"
        )
        return 0, 0

    except Exception as e:
        logger.error(f"Error getting contract info from Etherscan: {e}")
        logger.exception("Full traceback:")  # This will log the full stack trace
        return 0, 0


# Usage example
if __name__ == "__main__":
    # Load function signatures first
    function_signatures = load_function_signatures()

    # TODO: define these values before running the script
    chain_id = 1
    boring_vault_address = ""
    if boring_vault_address == "":
        raise ValueError("boring_vault_address is not defined")

    vault_name, authority_contract_address = get_vault_info(
        boring_vault_address, chain_id
    )
    from_block_etherscan, to_block_etherscan = get_contract_deployment_info(
        authority_contract_address, chain_id
    )
    logger.info(f"vault_name: {vault_name}")
    logger.info(f"authority_contract_address: {authority_contract_address}")
    logger.info(
        f"from_block_etherscan: {from_block_etherscan}, to_block_etherscan: {to_block_etherscan}"
    )

    abi_path = "protocol/scripts/abi/authority.json"
    event_names = [
        "UserRoleUpdated",
        "RoleCapabilityUpdated",
    ]  # add if needed "OwnershipTransferred"

    # Use cache by default, can be disabled with use_cache=False
    events = get_events(
        contract_address=authority_contract_address,
        chain_id=chain_id,
        abi_path=abi_path,
        event_names=event_names,
        from_block=from_block_etherscan,
        to_block=8823025,
        use_cache=True,  # Set to False to force blockchain scan
    )

    # Process events into table format
    table_rows, owner_address = process_events_to_table(
        events, function_signatures, chain_id
    )

    # Use authority.owner()
    if owner_address is None:
        owner_address = get_authority_owner(authority_contract_address, chain_id)

    # Save to markdown file
    save_markdown_table(
        authority_contract_address,
        table_rows,
        boring_vault_address,
        chain_id,
        vault_name,
        owner_address,
    )

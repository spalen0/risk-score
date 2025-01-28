from web3 import Web3
import json
import os
from pathlib import Path
from typing import Dict, List
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Load ABI files
def load_abi(file_path):
    with open(file_path) as f:
        abi_data = json.load(f)
        if isinstance(abi_data, dict):
            return abi_data["result"]
        elif isinstance(abi_data, list):
            return abi_data
        else:
            raise ValueError("Invalid ABI format")


class FactoryScanner:
    def __init__(self):
        self.factory_dir = Path("factory")
        self.strategy_dir = Path("strategy")
        self.providers: Dict[str, Web3] = {}

    def get_provider(self, chain_id: str) -> Web3:
        """Get or create Web3 provider for a chain."""
        if chain_id not in self.providers:
            rpc_url = os.getenv(f"RPC_{chain_id}")
            if not rpc_url:
                raise ValueError(f"Missing env variable RPC_{chain_id}")
            self.providers[chain_id] = Web3(Web3.HTTPProvider(rpc_url))
        return self.providers[chain_id]

    def scan_factory(
        self, chain_id: str, factory_address: str, factory_data: dict
    ) -> List[str]:
        """Scan a single factory for deployed strategies by checking deployment events."""
        provider = self.get_provider(chain_id)

        deployment = factory_data.get("deployment", {})
        if not deployment:
            raise ValueError(
                f"No deployment configuration found for factory {factory_address}"
            )

        # Use the deployEventAbi from factory_data
        event_abi = deployment.get("eventAbi", {})
        if not event_abi:
            raise ValueError(
                f"No deployEvent configuration found for factory {factory_address}"
            )

        logger.info(f"Using event config: {json.dumps(event_abi)}")
        factory_contract = provider.eth.contract(
            address=Web3.to_checksum_address(factory_address), abi=event_abi
        )

        if len(event_abi) != 1:
            raise ValueError(
                f"Event abi should contain only one event, found {len(event_abi)} events for {factory_address}"
            )

        # factory['deployEventAbi'][0] = eventAbi
        factory_config = event_abi[0]
        if factory_config["type"] != "event":
            raise ValueError(
                f"Event abi should contain only one event, found {factory_config['type']} for {factory_address}"
            )

        # Get block range for the last 25 hours because the script is run daily
        latest_block = provider.eth.block_number
        blocks_per_day = 7500  # 25 * 60 * 60 // 12
        from_block = latest_block - blocks_per_day

        strategies = []

        # Get event signature
        event_func = factory_contract.events[factory_config["name"]]
        logger.info(f"event_func: {event_func.event_name}")

        # Get event signature hash
        inputs = factory_config["inputs"]
        if not inputs:
            raise ValueError(f"Missing inputs for event {factory_config['name']}")

        event_signature = (
            f"{factory_config['name']}({','.join(input['type'] for input in inputs)})"
        )
        event_signature_hash = f"0x{Web3.keccak(text=event_signature).hex()}"

        # Ensure proper hex formatting for parameters
        filter_params = {
            "fromBlock": hex(from_block),
            "toBlock": hex(latest_block),
            "address": Web3.to_checksum_address(factory_address),
            "topics": [event_signature_hash],
        }
        logs = provider.eth.get_logs(filter_params)

        if not logs:
            logger.info(f"No logs found for blocks {from_block}-{latest_block}")
            return []

        # Process events
        strategy_param = deployment.get("eventStrategyParamName", "strategy")
        strategy_dir = self.strategy_dir / chain_id

        for log in logs:
            # Get the event object directly
            event_obj = factory_contract.events[event_func.event_name]()
            decoded_log = event_obj.process_log(log)

            if not decoded_log:
                logger.warning(f"Could not decode log: {log}")
                continue

            # logger.info(f"Decoded log: {decoded_log}")

            if "args" not in decoded_log:
                logger.warning("No args in decoded log")
                continue

            args = decoded_log["args"]

            if strategy_param in args:
                strategy_address = args[strategy_param]
                logger.info(strategy_address)
                if strategy_address:
                    strategy_file = strategy_dir / f"{strategy_address}.json"
                    if not strategy_file.exists():
                        strategies.append(strategy_address)
            else:
                raise ValueError(
                    f"No strategy param found in event {event_func.event_name}. Args: {args}"
                )

        return strategies

    def create_strategy_file(
        self, chain_id: str, strategy_address: str, factory_data: dict
    ):
        """Create a new strategy risk score file."""
        strategy_dir = self.strategy_dir / chain_id
        strategy_dir.mkdir(parents=True, exist_ok=True)

        strategy_file = strategy_dir / f"{strategy_address}.json"
        if not strategy_file.exists():
            risk_scores = factory_data.get("riskScore", {})
            strategy_data = {
                "riskLevel": factory_data.get("riskLevel", 0),
                "riskScore": {
                    "review": risk_scores.get("review", 0),
                    "testing": risk_scores.get("testing", 0),
                    "complexity": risk_scores.get("complexity", 0),
                    "riskExposure": risk_scores.get("riskExposure", 0),
                    "protocolIntegration": risk_scores.get("protocolIntegration", 0),
                    "centralizationRisk": risk_scores.get("centralizationRisk", 0),
                    "externalProtocolAudit": risk_scores.get(
                        "externalProtocolAudit", 0
                    ),
                    "externalProtocolCentralisation": risk_scores.get(
                        "externalProtocolCentralisation", 0
                    ),
                    "externalProtocolTvl": risk_scores.get("externalProtocolTvl", 0),
                    "externalProtocolLongevity": risk_scores.get(
                        "externalProtocolLongevity", 0
                    ),
                    "externalProtocolType": risk_scores.get("externalProtocolType", 0),
                    "comment": risk_scores.get("comment", ""),
                },
            }

            with open(strategy_file, "w") as f:
                json.dump(strategy_data, f, indent=4)
            logger.info(f"Created new strategy file: {strategy_file}")
        else:
            logger.info(f"strategy file already exists: {strategy_file}")

    def scan_all_factories(self):
        """Scan all factories across all chains."""
        for chain_dir in self.factory_dir.iterdir():
            if not chain_dir.is_dir() or not chain_dir.name.isdigit():
                continue

            chain_id = chain_dir.name
            logger.info(f"Scanning chain {chain_id}")

            for factory_file in chain_dir.glob("*.json"):
                factory_address = factory_file.stem
                # skip example factories
                if (
                    factory_address == "0x000000000000000000000000000000000000dead"
                    or factory_address == "0x90E46590c1f18Bb8aAF73b5A3a377f74B0eE2d83"
                ):
                    continue

                logger.info(f"Scanning factory {factory_address}")
                with open(factory_file) as f:
                    factory_data = json.load(f)

                strategies = self.scan_factory(chain_id, factory_address, factory_data)
                logger.info(f"Found {len(strategies)} strategies")
                for strategy in strategies:
                    self.create_strategy_file(chain_id, strategy, factory_data)


def main():
    scanner = FactoryScanner()
    scanner.scan_all_factories()


if __name__ == "__main__":
    main()

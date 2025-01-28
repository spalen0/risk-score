# Factory

This folder contains multiple folders, each folder represents a chain, name of the folder is the chain id (e.g. `1` for Ethereum mainnet).

Each folder contains JSON files of review strategy factories. Name of the file is the factory address. After the factory is reviewed, and deployed contract verified by SAM team, the factory file is added to specific folder depending on the network.

JSON structure:

- `riskLevel` is the final risk of the factory displayed on Yearn frontend risk bar.
- `riskScore` is object with detailed values of each risk category.
- `deployment` is object with `eventAbi` and `eventStrategyParamName` fields. `eventAbi` is abi of the event that is emitted when the strategy is deployed. `eventStrategyParamName` is the name of the parameter in the event that contains deployed strategy address.

If the strategy is created using factory, the strategy risk score file should be created in the `strategy` folder. This flow is handled by Github Actions. Periodically, Github Actions will fetch all factories from this folder and check on the blockchain if the factory created any new strategy. If the strategy is created, Github Actions will create new JSON file in the `strategy` folder using risk score values from the factory file.

## Adding a new factory

1. Create a new JSON file with name corresponding to the factory address in the `factory` folder. File must be in the correct folder. Name of the folder is the chain id, e.g. `1` for Ethereum mainnet.
2. JSON file must contain `riskLevel` and `riskScore` fields assigned by the SAM team.
3. JSON file must contain `deployment` object which contains `eventAbi` and `eventStrategyParamName` fields. `eventAbi` is abi of the event that is emitted when the strategy is deployed. `eventStrategyParamName` is the name of the parameter in the event that contains deployed strategy address.

For the reference check [file](./1/0x000000000000000000000000000000000000dead.json) or [MorphoCompounderFactory](./1/0x90E46590c1f18Bb8aAF73b5A3a377f74B0eE2d83.json). MorphoCompounderFactory is not used in the production because each Morpho vault must be evaluated individually. Morpho Vaults can have different currators and different markets, collaterals.

## Strategy Scanner

The strategy scanner is a script that scans the blockchain for new strategies created by factories. It is run by Github Actions every hour. The script fetches all factories from the `factory` folder and checks if the factory created any new strategy. If the strategy is created, the script creates a new JSON file in the `strategy` folder using risk score values from the factory file.

The script is located in the [`scripts/scan_factories.py`](../scripts/scan_factories.py) file.

### How to run the script manually

1. Clone the repository
2. Install dependencies, run `pip install -r requirements.txt`
3. Run `python scripts/scan_factories.py`

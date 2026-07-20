// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title EnergyTrading - escrow-backed immutable P2P energy trade ledger.
contract EnergyTrading {
    address public immutable settlementOperator;
    struct Trade {
        address seller;
        address buyer;
        uint256 energyWh;
        uint256 priceRsPaisa;
        uint256 timestamp;
        bool settled;
    }

    Trade[] public trades;
    mapping(address => uint256) public balances;

    event TradeSettled(uint256 indexed tradeId, address seller, address buyer, uint256 amount);
    event FundsDeposited(address indexed user, uint256 amount);
    event FundsWithdrawn(address indexed user, uint256 amount);

    constructor() { settlementOperator = msg.sender; }

    function deposit() external payable {
        require(msg.value > 0, "Deposit must be positive");
        balances[msg.sender] += msg.value;
        emit FundsDeposited(msg.sender, msg.value);
    }

    function settleTrade(address seller, address buyer, uint256 energyWh, uint256 priceRsPaisa) external {
        require(msg.sender == settlementOperator, "Only settlement operator");
        require(seller != address(0) && buyer != address(0), "Invalid participant");
        require(seller != buyer, "Participants must differ");
        require(energyWh > 0 && priceRsPaisa > 0, "Trade values must be positive");
        // The escrow uses wei. The oracle/backend supplies the comparable amount.
        uint256 amount = energyWh * priceRsPaisa;
        require(balances[buyer] >= amount, "Buyer escrow insufficient");
        balances[buyer] -= amount;
        balances[seller] += amount;
        trades.push(Trade(seller, buyer, energyWh, priceRsPaisa, block.timestamp, true));
        emit TradeSettled(trades.length - 1, seller, buyer, amount);
    }

    function withdraw(uint256 amount) external {
        require(amount > 0 && balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        (bool success,) = payable(msg.sender).call{value: amount}("");
        require(success, "Withdrawal failed");
        emit FundsWithdrawn(msg.sender, amount);
    }

    function getTrades() external view returns (Trade[] memory) { return trades; }
    function getBalance(address user) external view returns (uint256) { return balances[user]; }
}

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MonArcadeVault
 * @notice Minimal escrow and settlement vault for Mon Arcade matches on Monad Testnet.
 * @dev Stores native MON match deposits and settles payouts to verified winners.
 *      Authoritative game logic resides offchain on the Mon Arcade backend engine.
 */
contract MonArcadeVault {
    address public owner;
    mapping(address => bool) public operators;

    struct MatchDeposit {
        address depositor;
        uint256 amount;
        bool settled;
        address winner;
    }

    // matchId => MatchDeposit
    mapping(bytes32 => MatchDeposit) public matches;
    uint256 public totalEscrowed;

    // Reentrancy guard
    uint8 private _unlocked = 1;

    // Events
    event MatchDeposited(
        bytes32 indexed matchId,
        address indexed depositor,
        uint256 amount
    );

    event MatchSettled(
        bytes32 indexed matchId,
        address indexed winner,
        uint256 payout
    );

    event OperatorUpdated(address indexed operator, bool authorized);
    event EmergencyWithdrawn(address indexed to, uint256 amount);

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "MonArcadeVault: not owner");
        _;
    }

    modifier onlyAuthorized() {
        require(
            msg.sender == owner || operators[msg.sender],
            "MonArcadeVault: not authorized"
        );
        _;
    }

    modifier nonReentrant() {
        require(_unlocked == 1, "MonArcadeVault: reentrant call");
        _unlocked = 0;
        _;
        _unlocked = 1;
    }

    constructor() {
        owner = msg.sender;
        operators[msg.sender] = true;
        emit OperatorUpdated(msg.sender, true);
    }

    /**
     * @notice Authorize or revoke backend operator addresses for match settlement.
     */
    function setOperator(address operator, bool authorized) external onlyOwner {
        require(operator != address(0), "MonArcadeVault: zero address operator");
        operators[operator] = authorized;
        emit OperatorUpdated(operator, authorized);
    }

    /**
     * @notice Deposit native MON to fund a match escrow.
     * @param matchId Unique bytes32 match/session identifier.
     */
    function deposit(bytes32 matchId) external payable nonReentrant {
        require(msg.value > 0, "MonArcadeVault: zero deposit");
        require(matchId != bytes32(0), "MonArcadeVault: empty match id");
        require(
            matches[matchId].depositor == address(0),
            "MonArcadeVault: match already exists"
        );

        matches[matchId] = MatchDeposit({
            depositor: msg.sender,
            amount: msg.value,
            settled: false,
            winner: address(0)
        });

        totalEscrowed += msg.value;

        emit MatchDeposited(matchId, msg.sender, msg.value);
    }

    /**
     * @notice Settle a match and pay out the deposited MON to the winner.
     * @param matchId Unique bytes32 identifier of the match.
     * @param winner Recipient address that won the match.
     */
    function settle(bytes32 matchId, address payable winner)
        external
        onlyAuthorized
        nonReentrant
    {
        require(winner != address(0), "MonArcadeVault: invalid winner address");
        MatchDeposit storage matchInfo = matches[matchId];

        require(
            matchInfo.depositor != address(0),
            "MonArcadeVault: nonexistent match"
        );
        require(!matchInfo.settled, "MonArcadeVault: match already settled");

        uint256 payout = matchInfo.amount;
        matchInfo.settled = true;
        matchInfo.winner = winner;
        totalEscrowed -= payout;

        (bool success, ) = winner.call{value: payout}("");
        require(success, "MonArcadeVault: payout transfer failed");

        emit MatchSettled(matchId, winner, payout);
    }

    /**
     * @notice View match details.
     */
    function getMatch(bytes32 matchId)
        external
        view
        returns (
            address depositor,
            uint256 amount,
            bool settled,
            address winner
        )
    {
        MatchDeposit memory m = matches[matchId];
        return (m.depositor, m.amount, m.settled, m.winner);
    }

    /**
     * @notice Emergency recovery for genuinely unallocated funds exceeding active escrows.
     */
    function emergencyRecoverUnallocated(address payable to)
        external
        onlyOwner
        nonReentrant
    {
        require(to != address(0), "MonArcadeVault: invalid recipient");
        uint256 balance = address(this).balance;
        require(balance > totalEscrowed, "MonArcadeVault: no unallocated funds");
        uint256 unallocated = balance - totalEscrowed;

        (bool success, ) = to.call{value: unallocated}("");
        require(success, "MonArcadeVault: recovery transfer failed");

        emit EmergencyWithdrawn(to, unallocated);
    }

    receive() external payable {
        // Allow contract to receive native MON directly (unallocated treasury buffer)
    }
}

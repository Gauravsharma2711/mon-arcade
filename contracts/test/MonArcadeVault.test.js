const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("MonArcadeVault", function () {
  let vault;
  let owner;
  let operator;
  let player1;
  let player2;
  let unauthorized;

  const matchId1 = ethers.keccak256(ethers.toUtf8Bytes("match-001"));
  const matchId2 = ethers.keccak256(ethers.toUtf8Bytes("match-002"));
  const nonexistentMatchId = ethers.keccak256(ethers.toUtf8Bytes("match-ghost"));
  const depositAmount = ethers.parseEther("1.0");

  beforeEach(async function () {
    [owner, operator, player1, player2, unauthorized] = await ethers.getSigners();

    const MonArcadeVault = await ethers.getContractFactory("MonArcadeVault");
    vault = await MonArcadeVault.deploy();
    await vault.waitForDeployment();

    // Authorize operator
    await vault.connect(owner).setOperator(operator.address, true);
  });

  describe("Deployment & Authorization", function () {
    it("sets the deployer as owner and authorized operator", async function () {
      expect(await vault.owner()).to.equal(owner.address);
      expect(await vault.operators(owner.address)).to.be.true;
      expect(await vault.operators(operator.address)).to.be.true;
      expect(await vault.operators(unauthorized.address)).to.be.false;
    });

    it("rejects operator assignment from unauthorized caller", async function () {
      await expect(
        vault.connect(unauthorized).setOperator(unauthorized.address, true)
      ).to.be.revertedWith("MonArcadeVault: not owner");
    });
  });

  describe("Deposit Flow", function () {
    it("successfully deposits native MON and emits MatchDeposited event", async function () {
      await expect(
        vault.connect(player1).deposit(matchId1, { value: depositAmount })
      )
        .to.emit(vault, "MatchDeposited")
        .withArgs(matchId1, player1.address, depositAmount);

      const matchInfo = await vault.getMatch(matchId1);
      expect(matchInfo.depositor).to.equal(player1.address);
      expect(matchInfo.amount).to.equal(depositAmount);
      expect(matchInfo.settled).to.be.false;
      expect(matchInfo.winner).to.equal(ethers.ZeroAddress);

      expect(await vault.totalEscrowed()).to.equal(depositAmount);
      expect(await ethers.provider.getBalance(await vault.getAddress())).to.equal(depositAmount);
    });

    it("fails on zero-value deposit", async function () {
      await expect(
        vault.connect(player1).deposit(matchId1, { value: 0 })
      ).to.be.revertedWith("MonArcadeVault: zero deposit");
    });

    it("fails on empty match id", async function () {
      await expect(
        vault.connect(player1).deposit(ethers.ZeroHash, { value: depositAmount })
      ).to.be.revertedWith("MonArcadeVault: empty match id");
    });

    it("fails on duplicate deposit for the same match ID", async function () {
      await vault.connect(player1).deposit(matchId1, { value: depositAmount });

      await expect(
        vault.connect(player2).deposit(matchId1, { value: depositAmount })
      ).to.be.revertedWith("MonArcadeVault: match already exists");
    });
  });

  describe("Settlement Flow", function () {
    beforeEach(async function () {
      await vault.connect(player1).deposit(matchId1, { value: depositAmount });
    });

    it("allows authorized operator to settle and pays out winner", async function () {
      const winnerBalanceBefore = await ethers.provider.getBalance(player2.address);

      await expect(
        vault.connect(operator).settle(matchId1, player2.address)
      )
        .to.emit(vault, "MatchSettled")
        .withArgs(matchId1, player2.address, depositAmount);

      const winnerBalanceAfter = await ethers.provider.getBalance(player2.address);
      expect(winnerBalanceAfter - winnerBalanceBefore).to.equal(depositAmount);

      const matchInfo = await vault.getMatch(matchId1);
      expect(matchInfo.settled).to.be.true;
      expect(matchInfo.winner).to.equal(player2.address);
      expect(await vault.totalEscrowed()).to.equal(0);
    });

    it("allows contract owner to settle directly", async function () {
      await expect(
        vault.connect(owner).settle(matchId1, player1.address)
      )
        .to.emit(vault, "MatchSettled")
        .withArgs(matchId1, player1.address, depositAmount);

      const matchInfo = await vault.getMatch(matchId1);
      expect(matchInfo.settled).to.be.true;
    });

    it("fails when an unauthorized caller attempts settlement", async function () {
      await expect(
        vault.connect(unauthorized).settle(matchId1, unauthorized.address)
      ).to.be.revertedWith("MonArcadeVault: not authorized");
    });

    it("fails on duplicate settlement of already settled match", async function () {
      await vault.connect(operator).settle(matchId1, player2.address);

      await expect(
        vault.connect(operator).settle(matchId1, player2.address)
      ).to.be.revertedWith("MonArcadeVault: match already settled");
    });

    it("fails on invalid zero-address winner", async function () {
      await expect(
        vault.connect(operator).settle(matchId1, ethers.ZeroAddress)
      ).to.be.revertedWith("MonArcadeVault: invalid winner address");
    });

    it("fails on nonexistent match settlement", async function () {
      await expect(
        vault.connect(operator).settle(nonexistentMatchId, player1.address)
      ).to.be.revertedWith("MonArcadeVault: nonexistent match");
    });
  });

  describe("Emergency Recovery", function () {
    it("allows owner to recover genuinely unallocated funds beyond active escrows", async function () {
      // Direct donation / buffer
      await owner.sendTransaction({
        to: await vault.getAddress(),
        value: ethers.parseEther("0.5"),
      });

      // Active escrow
      await vault.connect(player1).deposit(matchId2, { value: depositAmount });

      // Owner recovers unallocated
      const recoveryRecipient = player2.address;
      const recipientBefore = await ethers.provider.getBalance(recoveryRecipient);

      await expect(vault.connect(owner).emergencyRecoverUnallocated(recoveryRecipient))
        .to.emit(vault, "EmergencyWithdrawn")
        .withArgs(recoveryRecipient, ethers.parseEther("0.5"));

      const recipientAfter = await ethers.provider.getBalance(recoveryRecipient);
      expect(recipientAfter - recipientBefore).to.equal(ethers.parseEther("0.5"));

      // Active escrow remains locked and safe
      expect(await vault.totalEscrowed()).to.equal(depositAmount);
      expect(await ethers.provider.getBalance(await vault.getAddress())).to.equal(depositAmount);
    });

    it("rejects emergency recovery from unauthorized account", async function () {
      await expect(
        vault.connect(unauthorized).emergencyRecoverUnallocated(unauthorized.address)
      ).to.be.revertedWith("MonArcadeVault: not owner");
    });

    it("reverts recovery if no unallocated funds exist", async function () {
      await vault.connect(player1).deposit(matchId1, { value: depositAmount });

      await expect(
        vault.connect(owner).emergencyRecoverUnallocated(owner.address)
      ).to.be.revertedWith("MonArcadeVault: no unallocated funds");
    });
  });
});

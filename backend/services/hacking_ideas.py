"""Hacking Ideas and Security Labs catalog service."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HackingIdea(BaseModel):
    id: str
    title: str
    category: str
    difficulty: str  # Beginner, Intermediate, Advanced
    goal: str
    learning_objectives: list[str] = Field(default_factory=list)
    suggested_tools: list[str] = Field(default_factory=list)
    lab_setup: str
    metadata: dict[str, Any] = Field(default_factory=dict)


_CATALOG: list[HackingIdea] = [
    # Wi-Fi Security Labs
    HackingIdea(
        id="wifi-rogue-ap-detection",
        title="Wi-Fi Rogue AP & Evil Twin Detection Lab",
        category="Wi-Fi",
        difficulty="Intermediate",
        goal=(
            "Build a private lab that detects unauthorized or rogue access points broadcasting"
            " target SSIDs."
        ),
        learning_objectives=[
            "802.11 beacon frame analysis",
            "BSSID/SSID mapping and OUI validation",
            "Channel monitoring and signal strength analysis",
            "Packet capture with tcpdump/Wireshark",
            "Building automated detection logic in Python",
        ],
        suggested_tools=[
            "Kali Linux",
            "Wireshark",
            "tcpdump",
            "Wireless adapter in monitor mode",
            "Python",
        ],
        lab_setup=(
            "Private lab with 2 wireless access points and a Kali Linux monitoring station on owned"
            " hardware."
        ),
    ),
    HackingIdea(
        id="wifi-wpa3-handshake-analysis",
        title="WPA2/WPA3 SAE Authentication Flow & Handshake Analysis",
        category="Wi-Fi",
        difficulty="Intermediate",
        goal=(
            "Inspect WPA2 4-way handshakes and WPA3 Simultaneous Authentication of Equals (SAE)"
            " exchanges in a private test environment."
        ),
        learning_objectives=[
            "WPA2 4-way handshake EAPOL frame structure",
            "WPA3 SAE Dragonfly key exchange mechanics",
            "Capturing 802.11 management frames cleanly",
            "Wireshark display filters for EAPOL and SAE frames",
        ],
        suggested_tools=["Wireshark", "aircrack-ng suite", "Kali Linux"],
        lab_setup=(
            "Isolated access point broadcasting a test WPA2/WPA3 SSID with a test client device."
        ),
    ),
    HackingIdea(
        id="wifi-guest-network-segmentation",
        title="Wi-Fi Guest Network & IoT Isolation Audit Lab",
        category="Wi-Fi",
        difficulty="Beginner",
        goal="Audit network isolation between guest wireless VLANs, IoT subnets, and primary LANs.",
        learning_objectives=[
            "802.1Q VLAN tagging and wireless SSID mapping",
            "Subnet scanning and ARP inspection",
            "Firewall rule verification for guest subnets",
            "Captive portal security analysis",
        ],
        suggested_tools=["Nmap", "Arp-scan", "Wireshark", "Router/VLAN switch"],
        lab_setup="Home or lab router with separate primary, guest, and IoT VLANs.",
    ),
    # Web Security Labs
    HackingIdea(
        id="web-jwt-security-review",
        title="JWT Security & Signature Validation Lab",
        category="Web",
        difficulty="Intermediate",
        goal=(
            "Build a vulnerable JWT authentication web app and implement secure token verification."
        ),
        learning_objectives=[
            "JWT header, payload, and signature structure",
            "Algorithm confusion (none vs HS256 vs RS256)",
            "Token expiration and revocation mechanisms",
            "Secure secret and key management",
        ],
        suggested_tools=["Python FastAPI", "Burp Suite / OWASP ZAP", "jwt.io"],
        lab_setup="Local Python FastAPI application running on localhost.",
    ),
    # Network Labs
    HackingIdea(
        id="net-dns-exfiltration-detection",
        title="DNS Tunneling & Query Exfiltration Detection",
        category="Network",
        difficulty="Advanced",
        goal="Simulate DNS query encapsulation and create a Zeek/Suricata detection rule.",
        learning_objectives=[
            "DNS query record types (TXT, NULL, CNAME)",
            "Entropy and subdomain length analysis",
            "Zeek script / Suricata rule writing",
            "PCAP analysis for abnormal DNS traffic",
        ],
        suggested_tools=["tcpdump", "Wireshark", "Zeek", "Suricata", "Python"],
        lab_setup="Local Linux virtual machine with Zeek or Suricata network monitor.",
    ),
    # Linux Security Labs
    HackingIdea(
        id="linux-privilege-capabilities",
        title="Linux Capabilities & SUID Audit Lab",
        category="Linux",
        difficulty="Intermediate",
        goal="Explore POSIX capabilities (CAP_SETUID, CAP_NET_ADMIN) vs traditional SUID binaries.",
        learning_objectives=[
            "POSIX capabilities model (getcap / setcap)",
            "SUID / SGID permission bit analysis",
            "Principle of least privilege for Linux binaries",
            "Auditing system binaries with find and GTFOBins concepts",
        ],
        suggested_tools=["Linux / Ubuntu / Kali", "getcap", "setcap", "find"],
        lab_setup="Disposable Linux virtual machine or Docker container.",
    ),
    # Windows / Active Directory Labs
    HackingIdea(
        id="win-event-log-hunting",
        title="Windows Security Event Log Threat Hunting Lab",
        category="Windows",
        difficulty="Intermediate",
        goal="Simulate administrative actions and analyze Event IDs 4624, 4672, 4688, and 7045.",
        learning_objectives=[
            "Windows Security Event ID classification",
            "Process creation tracking with command-line auditing",
            "Service installation detection (Event ID 7045)",
            "Querying event logs with PowerShell Get-WinEvent",
        ],
        suggested_tools=["Windows 10/11 or Server VM", "PowerShell", "Sysmon"],
        lab_setup=(
            "Isolated Windows virtual machine with Sysmon and Process Command Line auditing"
            " enabled."
        ),
    ),
    # Reverse Engineering Labs
    HackingIdea(
        id="re-elf-static-analysis",
        title="ELF Binary Static Analysis & Triage Lab",
        category="Reverse Engineering",
        difficulty="Intermediate",
        goal=(
            "Triage a compiled C ELF binary using static analysis tools without executing untrusted"
            " samples."
        ),
        learning_objectives=[
            "ELF header and section header analysis",
            "Inspecting symbol tables and string references",
            "Decompilation and disassembly with Ghidra or radare2",
            "Identifying import functions and security flags (NX, PIE, Canary)",
        ],
        suggested_tools=["readelf", "objdump", "strings", "Ghidra", "radare2"],
        lab_setup="Kali Linux or Linux development environment.",
    ),
    # Container / Cloud Security Labs
    HackingIdea(
        id="container-docker-security-audit",
        title="Docker Container Hardening & Rootless Setup Lab",
        category="Containers",
        difficulty="Beginner",
        goal=(
            "Audit a Dockerfile and container runtime for root execution, cap-add privileges, and"
            " mounted sockets."
        ),
        learning_objectives=[
            "Rootless Docker runtime setup",
            "Seccomp and AppArmor profiles for containers",
            "Detecting exposed Docker sockets (/var/run/docker.sock)",
            "Static analysis with Hadolint and Trivy",
        ],
        suggested_tools=["Docker", "Hadolint", "Trivy", "Linux"],
        lab_setup="Local Docker installation in a Linux environment.",
    ),
]


class HackingIdeasService:
    def list_ideas(self, category: str | None = None) -> list[HackingIdea]:
        if not category or category.lower() == "all":
            return _CATALOG
        return [idea for idea in _CATALOG if idea.category.lower() == category.lower()]

    def get_idea(self, idea_id: str) -> HackingIdea | None:
        for idea in _CATALOG:
            if idea.id == idea_id:
                return idea
        return None

    def start_lab_session(self, idea_id: str) -> dict[str, Any]:
        idea = self.get_idea(idea_id)
        if not idea:
            raise ValueError(f"Unknown lab idea: {idea_id}")

        prompt = f"""Lab Objective: {idea.title}
Category: {idea.category} | Difficulty: {idea.difficulty}

Goal:
{idea.goal}

Learning Objectives:
{chr(10).join(f"- {obj}" for obj in idea.learning_objectives)}

Suggested Tools:
{", ".join(idea.suggested_tools)}

Lab Setup:
{idea.lab_setup}

Let's begin this security lab! Please outline the first step."""

        return {
            "idea_id": idea.id,
            "title": idea.title,
            "category": idea.category,
            "prompt": prompt,
            "initial_tools": idea.suggested_tools,
        }

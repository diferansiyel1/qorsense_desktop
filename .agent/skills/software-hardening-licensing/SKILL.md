---
name: software-hardening-licensing
description: Professional-grade software protection, code hardening, and licensing management. Handles code obfuscation with PyArmor, DRM implementation, license key generation (RSA/AES), and subscription models. Use PROACTIVELY for commercializing desktop apps, protecting IP, or implementing secure licensing servers.
---

## Use this skill when

- Preparing a Python application for commercial release.
- Protecting source code from reverse engineering or unauthorized access.
- Implementing license key validation (offline or online).
- Setting up trial modes, feature-gating, or subscription-based access.
- Hardening software against common bypass techniques.

## Instructions

- Use **PyArmor** (latest) for advanced Python code obfuscation.
- Never store plain-text secrets or keys in the source code.
- Implement **asymmetric encryption (RSA)** for license signature verification.
- Combine code protection with **environment binding** (Hardware ID, MAC address).
- Always include a **graceful fallback** for licensing server downtime.

## Capabilities

### Code Protection & Obfuscation
- **PyArmor Mastery**: Obfuscating scripts, bundling dependencies, and runtime security.
- **Cross-Platform Hardening**: Windows-specific (PE), macOS (Mach-O), and Linux safety.
- **Anti-Debugging**: Implementing checks to detect debuggers or VM environments.
- **Dependency Guarding**: Protecting compiled `.so` / `.pyd` files.

### Licensing Models
- **Subscription Management**: Integration with Stripe/Paddle for recurring billing.
- **License Keys**: Generating and validating cryptographically secure keys (RSA-2048+).
- **Trial & Evergreen Models**: Implementing time-based access and perpetual licenses.
- **Feature Gating**: Dynamically enabling/disabling UI features based on license tier.

### DRM & Security
- **Hardware Binding**: Locking software to specific machines (Machine Fingerprinting).
- **Online Activation**: Building secure activation servers with FastAPI or Go.
- **Offline Validation**: Public-key verification for air-gapped systems.
- **Tamper Detection**: Verifying integrity of the executable and resource files.

### IP Commercialization
- **Packaging for Sales**: Designing the installer (Inno Setup, NSIS, DMG) to include license EULA.
- **Version Control per Tier**: Managing different builds (Lite, Pro, Enterprise).
- **Internal Audit Trails**: Logging activation events (privacy-compliant).

## Example Interactions
- "Obfuscate my PyQt app using PyArmor to prevent source code leaks."
- "Implement an RSA-based license key generator and validator in Python."
- "How do I bind this software to a specific hardware ID to prevent piracy?"
- "Set up a feature-gating system that unlocks 'Easy Mode' vs 'Pro Mode' via a license file."

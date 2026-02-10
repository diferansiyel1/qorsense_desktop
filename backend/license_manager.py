"""
License Manager for QorSense Desktop Application
Copyright © 2025 Pikolab R&D Ltd. Co. All Rights Reserved.

Hardware-locked licensing system using machine fingerprinting.
"""

import hashlib
import logging
import os
import platform
import uuid

logger = logging.getLogger("LicenseManager")

# License file location (relative to project root)
LICENSE_FILE = "license.dat"

# License salt loaded from environment variable for security
# NEVER commit actual salt values to source control
_LICENSE_SALT = os.environ.get("QORSENSE_LICENSE_SALT")

if not _LICENSE_SALT:
    logger.warning(
        "⚠️  QORSENSE_LICENSE_SALT not set in environment. "
        "License validation will use fallback mode. "
        "Set this variable in production for security."
    )
    # Fallback for development only - generates machine-specific salt
    import hashlib
    _machine_id = hashlib.sha256(
        f"{os.getenv('USER', 'default')}:{os.uname().nodename}".encode()
    ).hexdigest()[:16]
    _LICENSE_SALT = f"DEV_FALLBACK_{_machine_id}"


class LicenseManager:
    """
    Hardware-locked license manager.
    
    Generates and validates license keys based on machine-specific
    hardware identifiers (MAC address + hostname).
    """

    def __init__(self, license_file_path: str = None):
        """
        Initialize the license manager.
        
        Args:
            license_file_path: Optional custom path for license file.
                             Defaults to 'license.dat' in project root.
        """
        if license_file_path:
            self.license_file = license_file_path
        else:
            # Default: license.dat in the same directory as this module's parent
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.license_file = os.path.join(base_dir, "config", LICENSE_FILE)

    # Cache file for persistent machine ID
    _MACHINE_ID_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".qorsense")
    _MACHINE_ID_CACHE_FILE = os.path.join(_MACHINE_ID_CACHE_DIR, "machine_id.cache")

    def get_machine_id(self) -> str:
        """
        Generate a unique, stable machine fingerprint.
        
        Uses platform-specific hardware identifiers:
        - Windows: BIOS UUID via WMI
        - macOS: IOPlatformUUID via ioreg
        - Fallback: MAC address + hostname
        
        The ID is cached to a file for consistency across restarts.
        
        Returns:
            SHA-256 hash of the hardware identifier (first 32 chars)
        """
        try:
            # 1. Check cache first for consistency
            cached_id = self._load_cached_machine_id()
            if cached_id:
                logger.debug(f"Using cached machine ID: {cached_id[:8]}...")
                return cached_id

            # 2. Get platform-specific hardware identifier
            system = platform.system()
            if system == "Windows":
                hardware_id = self._get_windows_uuid()
            elif system == "Darwin":
                hardware_id = self._get_macos_uuid()
            else:
                hardware_id = self._get_fallback_id()

            # 3. Hash the hardware ID
            hash_obj = hashlib.sha256(hardware_id.encode('utf-8'))
            machine_id = hash_obj.hexdigest()[:32].upper()

            # 4. Cache for future consistency
            self._save_cached_machine_id(machine_id)

            logger.debug(f"Generated machine ID: {machine_id[:8]}...")
            return machine_id

        except Exception as e:
            logger.error(f"Error generating machine ID: {e}")
            raise RuntimeError(f"Failed to generate machine ID: {e}")

    def _get_windows_uuid(self) -> str:
        """Get BIOS UUID on Windows using WMI."""
        import subprocess
        try:
            result = subprocess.run(
                ["wmic", "csproduct", "get", "UUID"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                uuid_value = lines[1].strip()
                if uuid_value and uuid_value != "":
                    logger.debug("Retrieved Windows BIOS UUID")
                    return uuid_value
        except Exception as e:
            logger.warning(f"Failed to get Windows UUID: {e}")
        
        # Fallback if WMI fails
        return self._get_fallback_id()

    def _get_macos_uuid(self) -> str:
        """Get IOPlatformUUID on macOS using ioreg."""
        import subprocess
        try:
            result = subprocess.run(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                capture_output=True,
                text=True,
                timeout=5
            )
            import re
            match = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', result.stdout)
            if match:
                uuid_value = match.group(1)
                logger.debug("Retrieved macOS IOPlatformUUID")
                return uuid_value
        except Exception as e:
            logger.warning(f"Failed to get macOS UUID: {e}")
        
        # Fallback if ioreg fails
        return self._get_fallback_id()

    def _get_fallback_id(self) -> str:
        """Fallback: use MAC address + hostname."""
        mac_address = str(uuid.getnode())
        hostname = platform.node()
        fallback_id = f"{mac_address}:{hostname}"
        logger.debug("Using fallback ID (MAC + hostname)")
        return fallback_id

    def _load_cached_machine_id(self) -> str | None:
        """Load cached machine ID from file."""
        try:
            if os.path.exists(self._MACHINE_ID_CACHE_FILE):
                with open(self._MACHINE_ID_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cached_id = f.read().strip()
                    if cached_id and len(cached_id) == 32:
                        return cached_id
        except Exception as e:
            logger.debug(f"Could not load cached machine ID: {e}")
        return None

    def _save_cached_machine_id(self, machine_id: str) -> None:
        """Save machine ID to cache file for consistency."""
        try:
            os.makedirs(self._MACHINE_ID_CACHE_DIR, exist_ok=True)
            with open(self._MACHINE_ID_CACHE_FILE, 'w', encoding='utf-8') as f:
                f.write(machine_id)
            logger.debug(f"Cached machine ID to {self._MACHINE_ID_CACHE_FILE}")
        except Exception as e:
            logger.warning(f"Could not cache machine ID: {e}")

    def generate_license_key(self, machine_id: str) -> str:
        """
        Generate a license key for a given machine ID.
        
        The key is created by:
        1. Combining machine_id with secret salt
        2. Hashing with SHA-256
        3. Taking first 16 characters
        4. Formatting as XXXX-XXXX-XXXX-XXXX
        
        Args:
            machine_id: The machine fingerprint to generate key for
            
        Returns:
            Formatted license key (XXXX-XXXX-XXXX-XXXX)
        """
        try:
            # Combine machine ID with salt
            combined = f"{machine_id}:{_LICENSE_SALT}"

            # Generate hash
            hash_obj = hashlib.sha256(combined.encode('utf-8'))
            raw_key = hash_obj.hexdigest()[:16].upper()

            # Format as XXXX-XXXX-XXXX-XXXX
            formatted_key = '-'.join([
                raw_key[0:4],
                raw_key[4:8],
                raw_key[8:12],
                raw_key[12:16]
            ])

            logger.debug(f"Generated license key for machine: {machine_id[:8]}...")
            return formatted_key

        except Exception as e:
            logger.error(f"Error generating license key: {e}")
            raise RuntimeError(f"Failed to generate license key: {e}")

    def verify_license(self, input_key: str) -> bool:
        """
        Verify if the input license key is valid for this machine.
        
        Args:
            input_key: The license key to verify
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not input_key:
                return False

            # Normalize input (remove extra spaces, ensure uppercase)
            normalized_key = input_key.strip().upper()

            # Get expected key for this machine
            machine_id = self.get_machine_id()
            expected_key = self.generate_license_key(machine_id)

            is_valid = normalized_key == expected_key

            if is_valid:
                logger.info("License key verified successfully")
            else:
                logger.warning("License key verification failed")

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying license: {e}")
            return False

    def save_license(self, key: str) -> bool:
        """
        Save the license key to the license file.
        
        Args:
            key: The license key to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(self.license_file, 'w', encoding='utf-8') as f:
                f.write(key.strip())

            logger.info(f"License saved to {self.license_file}")
            return True

        except Exception as e:
            logger.error(f"Error saving license: {e}")
            return False

    def load_license(self) -> str | None:
        """
        Load the license key from the license file.
        
        Returns:
            The saved license key, or None if not found/error
        """
        try:
            if not os.path.exists(self.license_file):
                logger.debug("No license file found")
                return None

            with open(self.license_file, encoding='utf-8') as f:
                key = f.read().strip()

            if key:
                logger.debug("License loaded from file")
                return key
            logger.debug("License file is empty")
            return None

        except Exception as e:
            logger.error(f"Error loading license: {e}")
            return None

    def is_licensed(self) -> bool:
        """
        Check if a valid license exists.
        
        Returns:
            True if valid license is saved, False otherwise
        """
        saved_license = self.load_license()
        if saved_license:
            return self.verify_license(saved_license)
        return False

    def get_display_machine_id(self) -> str:
        """
        Get a display-friendly version of the machine ID.
        
        Returns:
            Machine ID formatted for display (with dashes for readability)
        """
        machine_id = self.get_machine_id()
        # Format as XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX (UUID-like)
        return f"{machine_id[:8]}-{machine_id[8:12]}-{machine_id[12:16]}-{machine_id[16:20]}-{machine_id[20:32]}"

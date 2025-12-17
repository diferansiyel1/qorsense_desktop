"""
License Manager for QorSense Desktop Application
Copyright © 2025 Pikolab R&D Ltd. Co. All Rights Reserved.

Hardware-locked licensing system using machine fingerprinting.
"""

import hashlib
import uuid
import platform
import os
import logging

logger = logging.getLogger("LicenseManager")

# License file location (relative to project root)
LICENSE_FILE = "license.dat"

# Secret salt for license key generation - DO NOT SHARE
_LICENSE_SALT = "PIKOLAB_SECRET_2025"


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
            self.license_file = os.path.join(base_dir, LICENSE_FILE)
    
    def get_machine_id(self) -> str:
        """
        Generate a unique machine fingerprint.
        
        Combines:
        - MAC address (uuid.getnode())
        - Hostname (platform.node())
        
        Returns:
            SHA-256 hash of the combined identifiers (first 32 chars)
        """
        try:
            mac_address = str(uuid.getnode())
            hostname = platform.node()
            
            # Combine identifiers
            raw_id = f"{mac_address}:{hostname}"
            
            # Hash the combination
            hash_obj = hashlib.sha256(raw_id.encode('utf-8'))
            machine_id = hash_obj.hexdigest()[:32].upper()
            
            logger.debug(f"Generated machine ID: {machine_id}")
            return machine_id
            
        except Exception as e:
            logger.error(f"Error generating machine ID: {e}")
            raise RuntimeError(f"Failed to generate machine ID: {e}")
    
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
            
            with open(self.license_file, 'r', encoding='utf-8') as f:
                key = f.read().strip()
            
            if key:
                logger.debug("License loaded from file")
                return key
            else:
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

# Diftar to EnergyID

A small utility to export data from "Mijn Diftar" to EnergyID.

This script takes the 100 most recent collection entries from the Diftar site and uploads them to EnergyID.

## Configuration

Create a file called `diftar2energyid.toml` with the following:

```toml
[diftar]
username="username"  # Username or Rijksregisternummer. Must be in quotes!
password="password"  # Diftar website password

[energyid]
url="webhookURL"    # Activate one here: https://app.energyid.eu/integrations/WebhookIn
    
    # I suggest you leave this alone, but you can change the ID & names here.
    # Since they don't charge for Papier/Karton, it's not listed on the site.
    # Only GFT + REST are supported.
    [energyid.GFT]
    remoteId="diftar-gft"
    remoteName="GFT"
    [energyid.REST]
    remoteId="diftar-rest"
    remoteName="Restafval"

```

## Usage

1. Install requirements.txt.
2. Create the config file mentioned above.
3. Run the script.

Be aware: There is a rate limit on the webhooks API. I suggest only running this script every day, or even every week. I recommend a con job.

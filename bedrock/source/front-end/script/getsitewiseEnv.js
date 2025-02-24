const {
    IoTSiteWiseClient,
    ListAssetsCommand,
    ListAssociatedAssetsCommand,
    ListAssetPropertiesCommand,
  } = require("@aws-sdk/client-iotsitewise");
  const { fromEnv } = require("@aws-sdk/credential-providers");

  class SitewiseAssetModel {
    constructor(client) {
      this.client = client;
    }
  
    // Helper method to list all top-level assets
    async listAllTopLevelAssets() {
      const input = {
        filter: "TOP_LEVEL", // To list only top-level assets
        maxResults: 50,      // You can adjust the max results per page if needed
      };
  
      let assets = [];
      let nextToken;
  
      try {
        do {
          const command = new ListAssetsCommand({ ...input, nextToken });
          const response = await this.client.send(command);
  
          if (response.assetSummaries) {
            assets = assets.concat(response.assetSummaries);
          }
  
          nextToken = response.nextToken;
        } while (nextToken);
  
        return assets;
      } catch (error) {
        console.error("Error listing top-level assets:", error);
        return null;
      }
    }
  
    // Method to get Brewery asset
    async getBreweryAsset() {
      try {
        const assets = await this.listAllTopLevelAssets();
  
        if (!assets) {
          throw new Error("Unable to get assets");
        } else {
          for (const asset of assets) {
            if (asset.id && asset.name === "Breweries") {
              return asset;
            }
          }
        }
      } catch (error) {
        console.error("Error listing assets and properties:", error);
        return null;
      }
    }
  
    async getChildAssets(assetId, hierarchyId) {
      const input = {
        hierarchyId: hierarchyId,
        traversalDirection: "CHILD",
        maxResults: 50,
        assetId: assetId,
      };
  
      let allAssets = [];
      let nextToken;
  
      try {
        do {
          const command = new ListAssociatedAssetsCommand({ ...input, nextToken });
          const response = await this.client.send(command);
  
          if (response.assetSummaries) {
            allAssets = allAssets.concat(response.assetSummaries);
  
            for (const asset of response.assetSummaries) {
              if (!asset.hierarchies) return allAssets;
              for (const hierarchy of asset.hierarchies) {
                if (asset.id && hierarchy.id) {
                  const childAssets = await this.getChildAssets(asset.id, hierarchy.id);
                  allAssets = allAssets.concat(childAssets);
                }
              }
            }
          }
  
          nextToken = response.nextToken;
        } while (nextToken);
  
        return allAssets;
      } catch (error) {
        console.error("Error retrieving assets:", error);
        throw error;
      }
    }
  
    async getChildAssetProperty(assetID) {
      const input = {
        assetId: assetID,
        maxResults: 50,
      };
  
      let nextToken;
      let properties = [];
  
      try {
        do {
          const command = new ListAssetPropertiesCommand(input);
          const response = await this.client.send(command);
  
          if (response.assetPropertySummaries) {
            properties = properties.concat(response.assetPropertySummaries);
          }
  
          nextToken = response.nextToken;
        } while (nextToken);
        return properties
      } catch (err) {
        console.error("Error retrieving asset properties:", err);
      }
    }
  
    async getAssetModel() {
      const sitwiseModelObj = {
        breweryAssetID: "",
        roasterAssetID: "",
        roasterProperities: {
          holdTimeID: "",
          temperature: "",
          scrap: "",
          oeePer5min: "",
          performancePer5min: "",
          qualityPer5min: "",
          utilizationPer5min: ""
        },
      };
  
      try {
        const breweryAsset = await this.getBreweryAsset();
  
        if (!breweryAsset || !breweryAsset.id || !breweryAsset.hierarchies) {
          throw new Error("Brewery asset not found or incomplete.");
        }
  
        sitwiseModelObj.breweryAssetID = breweryAsset.id;
  
        const allAssets = await this.getChildAssets(breweryAsset.id, breweryAsset.hierarchies[0].id);
  
        const roasterAsset = allAssets.find((asset) => asset.name === "Roaster100");
        if (roasterAsset && roasterAsset.id) {
          sitwiseModelObj.roasterAssetID = roasterAsset.id;
  
          const roasterProperties = await this.getChildAssetProperty(roasterAsset.id);
  
          if (roasterProperties) {
            roasterProperties.forEach((prop) => {
              if (prop.alias === "/Breweries/IrvinePlant/Roasting/Roaster100/HoldTime_PT" && prop.id) {
                sitwiseModelObj.roasterProperities.holdTimeID = prop.id;
              } else if (prop.alias === "/Breweries/IrvinePlant/Roasting/Roaster100/Temperature_PV" && prop.id) {
                sitwiseModelObj.roasterProperities.temperature = prop.id;
              } else if (prop.alias === "/Breweries/IrvinePlant/Roasting/Roaster100/Scrap" && prop.id) {
                sitwiseModelObj.roasterProperities.scrap = prop.id;
              } else if (prop.alias === "/Breweries/IrvinePlant/Roasting/Roaster100/OEEPer5min" && prop.id) {
                sitwiseModelObj.roasterProperities.oeePer5min = prop.id;
              } else if (prop.alias === "/Breweries/IrvinePlant/Roasting/Roaster100/PerformancePer5min" && prop.id) {
                sitwiseModelObj.roasterProperities.performancePer5min = prop.id;
              } else if (prop.alias === "/Breweries/IrvinePlant/Roasting/Roaster100/QualityPer5min" && prop.id) {
                sitwiseModelObj.roasterProperities.qualityPer5min = prop.id;
              } else if (prop.alias === "/Breweries/IrvinePlant/Roasting/Roaster100/UtilizationPer5min" && prop.id) {
                sitwiseModelObj.roasterProperities.utilizationPer5min = prop.id;
              }
            });
          }
        }
  
        return sitwiseModelObj;
      } catch (error) {
        console.error("Error building asset model:", error);
        throw error;
      }
    }
  }
  

const client = new IoTSiteWiseClient({ 
    region: "us-east-1",
    credentials: fromEnv() 
});

const sitewiseModel = new SitewiseAssetModel(client);

(async () => {
  const assetModel = await sitewiseModel.getAssetModel();
  console.log(JSON.stringify(assetModel, null, 2));
})();
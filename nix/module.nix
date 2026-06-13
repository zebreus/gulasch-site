{ self }:
{ config, lib, pkgs, ... }:

let
  cfg = config.services.gulasch-sites;
  sitePackage = self.packages.${pkgs.stdenv.hostPlatform.system}.gulasch-sites;

  mkHost = name: root: lib.nameValuePair "${name}.${cfg.baseDomain}" {
    inherit root;
    forceSSL = cfg.forceSSL;
    enableACME = cfg.enableACME;
    extraConfig = ''
      add_header Cache-Control "${cfg.cacheControl}" always;
    '';
  };
in
{
  options.services.gulasch-sites = {
    enable = lib.mkEnableOption "static gulasch.site nginx sites";

    baseDomain = lib.mkOption {
      type = lib.types.str;
      default = "gulasch.site";
      description = "Base domain used for the exported static sites.";
    };

    enableACME = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Enable ACME certificates for the generated nginx virtual hosts.";
    };

    forceSSL = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Redirect HTTP to HTTPS for the generated nginx virtual hosts.";
    };

    cacheControl = lib.mkOption {
      type = lib.types.str;
      default = "public, max-age=300";
      description = "Cache-Control header for static site responses.";
    };
  };

  config = lib.mkIf cfg.enable {
    services.nginx.enable = true;

    services.nginx.virtualHosts = lib.listToAttrs [
      (mkHost "ocpncord" "${sitePackage}/ocpncord")
      (mkHost "pokemon" "${sitePackage}/pokemon")
      (mkHost "drive" "${sitePackage}/drive")
      (mkHost "aisaas" "${sitePackage}/aisaas")
      (mkHost "c3cock" "${sitePackage}/c3cock")
      (mkHost "testwebseite" "${sitePackage}/testwebseite")
      (mkHost "testwebseite2" "${sitePackage}/testwebseite2")
      (mkHost "chat" "${sitePackage}/chat")
      (mkHost "angular" "${sitePackage}/angular")
    ];
  };
}

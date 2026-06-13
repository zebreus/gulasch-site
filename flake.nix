{
  description = "Static gulasch.site web properties and NixOS nginx module";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          gulasch-sites = pkgs.stdenvNoCC.mkDerivation {
            pname = "gulasch-sites";
            version = "0.1.0";
            src = ./.;

            dontConfigure = true;
            dontBuild = true;

            installPhase = ''
              runHook preInstall
              mkdir -p "$out"
              cp -R sites/ocpncord "$out/ocpncord"
              cp -R sites/pokemon "$out/pokemon"
              cp -R sites/drive "$out/drive"
              cp -R sites/aisaas "$out/aisaas"
              cp -R sites/c3cock "$out/c3cock"
              runHook postInstall
            '';
          };

          default = self.packages.${system}.gulasch-sites;
        });

      nixosModules.default = import ./nix/module.nix { inherit self; };
      nixosModules.gulasch-sites = self.nixosModules.default;
    };
}

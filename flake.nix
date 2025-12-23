{
  description = ''
    A extremely simple cross-platform clipboard synchronization tool using WebSockets.
    Note: On Linux, it depends on xclip or xsel (in x11), or wl-clipboard (in wayland).
    https://github.com/GOKORURI007/sync-clipboard
  '';

  inputs = {
    nixpkgs.url = "nixpkgs";
  };

  outputs =
    { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
      pkgsFor = system: import nixpkgs { inherit system; };
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = pkgsFor system;
          pythonPkgs = pkgs.python3Packages;
          deps = with pythonPkgs; [
            websockets
            click
            pyperclip
          ];
        in
        {
          default = pkgs.stdenv.mkDerivation {
            pname = "sync-clipboard";
            version = "0.1.0";
            src = ./.;

            nativeBuildInputs = [ pkgs.makeWrapper ];
            buildInputs = [ pkgs.python3 ] ++ deps;

            installPhase = ''
              mkdir -p $out/bin
              cp sync-clipboard.py $out/bin/.sync-clipboard-wrapped

              makeWrapper ${pkgs.python3}/bin/python3 $out/bin/sync-clipboard \
                --add-flags "$out/bin/.sync-clipboard-wrapped" \
                --prefix PYTHONPATH : "$PYTHONPATH"
            '';
          };
        }
      );

      # nix develop
      devShells = forAllSystems (
        system:
        let
          pkgs = pkgsFor system;
        in
        {
          default = pkgs.mkShell {
            buildInputs = [
              (pkgs.python3.withPackages (
                ps: with ps; [
                  websockets
                  click
                  pyperclip
                ]
              ))
            ];
          };
        }
      );

      # nix run
      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/sync-clipboard";
        };
      });
    };
}

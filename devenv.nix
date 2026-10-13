{ pkgs, lib, ... }:

let
  hugrenv = pkgs.callPackage ./hugrenv.nix {};
in
{
  env.LLVM_SYS_211_PREFIX = "${hugrenv}";

  packages = [
    hugrenv
    pkgs.libffi
    pkgs.just
    pkgs.graphviz

  ]
  ++ lib.optionals pkgs.stdenv.isDarwin (
    [ pkgs.zlib pkgs.xz ]
  );

  enterShell = ''
    if [ "$(uname)" = "Darwin" ]; then
      export DYLD_LIBRARY_PATH="${hugrenv}/lib:${hugrenv}/lib64:$DYLD_LIBRARY_PATH"
    else
      export LD_LIBRARY_PATH="${hugrenv}/lib:${hugrenv}/lib64:$LD_LIBRARY_PATH"
    fi
    which bencher
    [[ $? != 0 ]] && curl --proto '=https' --tlsv1.2 -sSfL https://bencher.dev/download/install-cli.sh | sh
  '';

  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
    venv.enable = true;
    version = "3.14";
  };

  languages.rust = {
    channel = "stable";
    enable = true;
    components = [ "rustc" "cargo" "clippy" "rustfmt" "rust-analyzer" ];
  };

}

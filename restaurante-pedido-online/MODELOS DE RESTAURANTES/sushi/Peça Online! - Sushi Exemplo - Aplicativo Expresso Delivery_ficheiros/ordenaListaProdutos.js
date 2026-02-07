function ordenaListaProdutoComposto(tipo_ordenacao, lista){
  if(tipo_ordenacao == 'alfabetica') {
      let array_pronto = [];
      let array_subcategorias = new Set();
      for(let i = 0; i < lista.length; i++){
          array_subcategorias.add(lista[i].sabor_categoriaid);
      }

      for(let indice of array_subcategorias){
          let array = lista.filter(function(produto){
              return produto.sabor_categoriaid == indice;
          });
          array.sort(function(a, b) {
              if(a.sabor_nome.toUpperCase() < b.sabor_nome.toUpperCase()) {
                  return -1;
              } else {
                  return true;
              }
          });
          array_pronto = array_pronto.concat(array);
      }
      return array_pronto;
  }

  if(tipo_ordenacao == 'menor_preco'){
      let array_pronto = [];
      let array_subcategorias = new Set();
      for(let i = 0; i < lista.length; i++){
          array_subcategorias.add(lista[i].sabor_categoriaid);
      }

      for(let indice of array_subcategorias){
          let array = lista.filter(function(produto){
              return produto.sabor_categoriaid == indice;
          });
          array.sort(function(a, b) {
              if(parseFloat(a.sabor_precopromo) < parseFloat(b.sabor_precopromo)) {
                  return -1;
              } else {
                  return true;
              }
          });
          array_pronto = array_pronto.concat(array);
      }
      return array_pronto;
  }
  if(tipo_ordenacao == 'maior_preco'){
      let array_pronto = [];
      let array_subcategorias = new Set();
      for(let i = 0; i < lista.length; i++){
          array_subcategorias.add(lista[i].sabor_categoriaid);
      }

      for(let indice of array_subcategorias){
          let array = lista.filter(function(produto){
              return produto.sabor_categoriaid == indice;
          });
          array.sort(function(a, b) {
              if(parseFloat(a.sabor_precopromo) > parseFloat(b.sabor_precopromo)) {
                  return -1;
              } else {
                  return true;
              }
          });
          array_pronto = array_pronto.concat(array);
      }
      return array_pronto;
  }
  if(tipo_ordenacao == 'manual'){
      let array_pronto = [];
      let array_subcategorias = new Set();
      for(let i = 0; i < lista.length; i++){
          array_subcategorias.add(lista[i].sabor_categoriaid);
      }

      for(let indice of array_subcategorias){
          let array = lista.filter(function(produto){
              return produto.sabor_categoriaid == indice;
          });
          array.sort(function(a, b) {
              if(parseInt(a.sabor_ordem) < parseInt(b.sabor_ordem)) {
                  return -1;
              } else {
                  return true;
              }
          });
          array_pronto = array_pronto.concat(array);
      }
      return array_pronto;
  }
}

function ordenaListaProdutoCompostoDesktop(tipo_ordenacao, lista){
  if(tipo_ordenacao == 'alfabetica') {
      let array_pronto = [];
      let array_subcategorias = new Set();
      for(let i = 0; i < lista.length; i++){
          array_subcategorias.add(lista[i].sabor_categoriaid);
      }

      for(let indice of array_subcategorias){
          let array = lista.filter(function(produto){
              return produto.sabor_categoriaid == indice;
          });
          array.sort(function(a, b) {
              if(a.sabor_nome.toUpperCase() < b.sabor_nome.toUpperCase()) {
                  return -1;
              } else {
                  return true;
              }
          });
          array_pronto = array_pronto.concat(array);
      }
      return array_pronto;
  }

  if(tipo_ordenacao == 'menor_preco'){
      let array_pronto = [];
      let array_subcategorias = new Set();
      for(let i = 0; i < lista.length; i++){
          array_subcategorias.add(lista[i].sabor_categoriaid);
      }

      for(let indice of array_subcategorias){
          let array = lista.filter(function(produto){
              return produto.sabor_categoriaid == indice;
          });
          array.sort(function(a, b) {
              if(parseFloat(a.sabor_preco) < parseFloat(b.sabor_preco)) {
                  return -1;
              } else {
                  return true;
              }
          });
          array_pronto = array_pronto.concat(array);
      }
      return array_pronto;
  }
  if(tipo_ordenacao == 'maior_preco'){
      let array_pronto = [];
      let array_subcategorias = new Set();
      for(let i = 0; i < lista.length; i++){
          array_subcategorias.add(lista[i].sabor_categoriaid);
      }

      for(let indice of array_subcategorias){
          let array = lista.filter(function(produto){
              return produto.sabor_categoriaid == indice;
          });
          array.sort(function(a, b) {
              if(parseFloat(a.sabor_preco) > parseFloat(b.sabor_preco)) {
                  return -1;
              } else {
                  return true;
              }
          });
          array_pronto = array_pronto.concat(array);
      }
      return array_pronto;
  }
  if(tipo_ordenacao == 'manual'){
      let array_pronto = [];
      let array_subcategorias = new Set();
      for(let i = 0; i < lista.length; i++){
          array_subcategorias.add(lista[i].sabor_categoriaid);
      }

      for(let indice of array_subcategorias){
          let array = lista.filter(function(produto){
              return produto.sabor_categoriaid == indice;
          });
          array.sort(function(a, b) {
              if(parseInt(a.sabor_ordem) < parseInt(b.sabor_ordem)) {
                  return -1;
              } else {
                  return true;
              }
          });
          array_pronto = array_pronto.concat(array);
      }
      return array_pronto;
  }
}

function ordenaListaProdutoSimplesPromosDesktop(tipo_ordenacao, lista){
  if(!Array.isArray(lista)){
    return lista;
  }
  let lista_pronta = lista;
  if(tipo_ordenacao == 'alfabetica') {
    lista_pronta.sort(function(a, b) {
        if(a.sabor_nome.toUpperCase() < b.sabor_nome.toUpperCase()) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
  if(tipo_ordenacao == 'menor_preco'){
    lista_pronta.sort(function(a, b) {
        if(parseFloat(a.sabor_preco) < parseFloat(b.sabor_preco)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
  if(tipo_ordenacao == 'maior_preco'){
    lista_pronta.sort(function(a, b) {
        if(parseFloat(a.sabor_preco) > parseFloat(b.sabor_preco)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
  if(tipo_ordenacao == 'manual'){
    lista_pronta.sort(function(a, b) {
        if(parseInt(a.sabor_ordem) < parseInt(b.sabor_ordem)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
}

function ordenaListaProdutoCompostoComboDesktop(tipo_ordenacao, lista, tamanho){
  if(!Array.isArray(lista)){
    return lista;
  }
  let lista_pronta = lista;
  if(tipo_ordenacao == 'alfabetica') {
    lista_pronta.sort(function(a, b) {
        if(a.sabor_nome.toUpperCase() < b.sabor_nome.toUpperCase()) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }

  if(tipo_ordenacao == 'menor_preco'){
    lista_pronta.sort(function(a, b) {
      let precoA = 0.00;
      let precoB = 0.00;
      for(let x = 0; x < a.sabor_precostamanhos.length; x++) {
        if(a.sabor_precostamanhos[x].sabor_precotamanhos_codtamanho == tamanho) {
          precoA = a.sabor_precostamanhos[x].sabor_precotamanhos_precopromo;
        }
      }
      for(let x = 0; x < b.sabor_precostamanhos.length; x++) {
        if(b.sabor_precostamanhos[x].sabor_precotamanhos_codtamanho == tamanho) {
          precoB = b.sabor_precostamanhos[x].sabor_precotamanhos_precopromo;
        }
      }
        if(parseFloat(precoA) < parseFloat(precoB)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
  if(tipo_ordenacao == 'maior_preco'){
    lista_pronta.sort(function(a, b) {
      let precoA = 0.00;
      let precoB = 0.00;
      for(let x = 0; x < a.sabor_precostamanhos.length; x++) {
        if(a.sabor_precostamanhos[x].sabor_precotamanhos_codtamanho == tamanho) {
          precoA = a.sabor_precostamanhos[x].sabor_precotamanhos_precopromo;
        }
      }
      for(let x = 0; x < b.sabor_precostamanhos.length; x++) {
        if(b.sabor_precostamanhos[x].sabor_precotamanhos_codtamanho == tamanho) {
          precoB = b.sabor_precostamanhos[x].sabor_precotamanhos_precopromo;
        }
      }
        if(parseFloat(precoA) > parseFloat(precoB)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
  if(tipo_ordenacao == 'manual'){
    lista_pronta.sort(function(a, b) {
        if(parseInt(a.sabor_ordem) < parseInt(b.sabor_ordem)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
}

function ordenaListaComplementos(tipo_ordenacao, lista){
  if(!Array.isArray(lista)){
    return lista;
  }
  let lista_pronta = lista;
  if(tipo_ordenacao == 'alfabetica') {
    lista_pronta.sort(function(a, b) {
        let nomeA = a.borda_nome ? a.borda_nome : a.massa_nome; 
        let nomeB = b.borda_nome ? b.borda_nome : b.massa_nome; 
        if(nomeA.toUpperCase() < nomeB.toUpperCase()) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
  if(tipo_ordenacao == 'menor_preco'){
    lista_pronta.sort(function(a, b) {
        let precoA = a.borda_preco ? a.borda_preco : a.massa_preco; 
        let precoB = b.borda_preco ? b.borda_preco : b.massa_preco; 
        if(parseFloat(precoA) < parseFloat(precoB)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
  if(tipo_ordenacao == 'maior_preco'){
    lista_pronta.sort(function(a, b) {
        let precoA = a.borda_preco ? a.borda_preco : a.massa_preco; 
        let precoB = b.borda_preco ? b.borda_preco : b.massa_preco; 
        if(parseFloat(precoA) > parseFloat(precoB)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
  if(tipo_ordenacao == 'manual'){
    lista_pronta.sort(function(a, b) {
        let ordemA = a.borda_ordem ? a.borda_ordem : a.massa_ordem; 
        let ordemB = b.borda_ordem ? b.borda_ordem : b.massa_ordem; 
        if(parseFloat(ordemA) < parseFloat(ordemB)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
}

function ordenaListaComposicoes(tipo_ordenacao, lista){
  if(!Array.isArray(lista)){
    return lista;
  }
  let lista_pronta = lista;
  if(tipo_ordenacao == 'alfabetica') {
    lista_pronta.sort(function(a, b) {
        if(a.NOME.toUpperCase() < b.NOME.toUpperCase()) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
  if(tipo_ordenacao == 'menor_preco'){
    lista_pronta.sort(function(a, b) { 
        if(parseFloat(a.PRECO) < parseFloat(b.PRECO)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
  if(tipo_ordenacao == 'maior_preco'){
    lista_pronta.sort(function(a, b) {
        if(parseFloat(a.PRECO) > parseFloat(b.PRECO)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
  if(tipo_ordenacao == 'manual'){
    lista_pronta.sort(function(a, b) { 
        if(parseFloat(a.ORDEM) < parseFloat(b.ORDEM)) {
            return -1;
        } else {
            return true;
        }
    });
    return lista_pronta;
  }
}

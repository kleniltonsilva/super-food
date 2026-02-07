/* 
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
function init_combinado(){
    
    var infocombo = $("#montador_combo").data("combo-infos");
    
    var dados = {
        data_cod       : infocombo.combo_id,
        data_hash      : $("#montador_combo").data("combo-hash")
    };
    
    $.ajax({
        method: "POST",
        url: "/exec/montadoritem/iniciarcombinado/",
        data: dados,
        dataType : "json"
    }).done(function( msg ) {
        if(msg.res === true){
            dadoscnb = msg.dados;
            //var codbcombo = msg.dados.codigo;
            //set_itemsemipronto(msg.dados,codconfig);   
            reendCorpoCombinado(false);
        }else if(msg.res === false){
            alert("erro");
            //hideLoading();
        }else{
            alert("erro");
            //hideLoading();
        }
    }).fail(function(esd,sde){
        alert("falha ao executar ação");
        //hideLoading();
    });
    
}

function show_listaSabores_comb(){    
    //$('.esmaecer_montador').addClass('blackesm');
    //$('.listadesaboresescolher').stop().animate({left: '0px'}, 400);
    $('.esmaecer_montador').stop().fadeIn(1000);
    
    gggf_combinado = setInterval(function(){
        var hjk = $( ".cont_abascombo" ).scrollTop()+16; //document.getElementsByClassName("cont_abascombo")[0].scrollHeight - 362;

        if(hjk>16){
                $(".listadesaboresescolher").css("top",hjk+"px");

                $(".esmaecer_montador").css("top",hjk+"px");
        }
    },0);
    
}
function hide_listaSabores_comb(){    
    //$('.esmaecer_montador').addClass('blackesm');
    //$('.listadesaboresescolher').stop().animate({left: '0px'}, 400);
    $('.esmaecer_montador').stop().fadeOut(300);
    $(".listadesaboresescolher").fadeOut(300);
}

function reendCorpoCombinado(dados, hash){ 
    $("#montador_combo").addClass("combocombinado");
    var htmcont = "";
    var firstaba = false;
    var cntitens = dados.length;
    var arrRandAbas = [];
    var arrListaUmSabor = [];
    var cnt_umsabor = 0;
    var arrListaUmItem = [];
    var cnt_umitem = 0;
    
    htmcont += "<div class='cont_abascombo combocombinado' data-combo-confitem data-dadosdoitematual data-dadositem >";
    htmcont += "<div class='esmaecer_montador smaesertroca blackesm' style='display: none;'></div>";
    
    for(var i=0;i<cntitens;i++){        
        var idsessao = dados[i].sessao;
        var editavel = dados[i].editavel;
        var dadossessao = get_dadosSessao(idsessao);
        var tamanhos = dados[i].tamanhos;
        var sabores = dados[i].sabores;
        var qtditem = dados[i].quantidade;
        
        if(dadossessao !== false){
          var qtdtamanhos = tamanhos.length;
          
          var tipomontador = dadossessao.sessao_paginamontador;
          var icone = dadossessao.sessao_icone;
          var tipoicone = dadossessao.sessao_tipoicone;
          var nome = dadossessao.sessao_nome;
          var targetaba = gerarValor(8,true,true);
          arrRandAbas[i] = targetaba;
          firstaba = (firstaba === false)? targetaba : firstaba;
          
          var overf = "";
          if(editavel !== true){
              overf = "style='overflow-y: auto;'";
          }
          dados[i].sessao_tipoordenacao = dadossessao.sessao_tipoordenacao;
          htmcont += reendListaItemSimples_combinado(dados[i]);
        }
    }
    htmcont +="</div>";
    
    $(".abas_combo").html("");
    $("#content_combo").html(htmcont);
    $(".cont_abascombo").show();
    $(".nano").nanoScroller();
    $("#btnfinalizacombo").addClass("ativo");
    $(".btnAvancar_combo").hide();
    $(".btnVoltar_combo").hide();
    $('#btnfinalizacombo').animateCss('tada');

}

function rendItensTroca(dados){
    var hashcombo = $("#montador_combo").data("combo-hash");
    var ddhash = dados.hash;
    var codconf = dados.codconfig;
    
    var contlistasabores = sabores_itens.length;    
    var htmcont = ""; 
    if(dados.sabores_troca != undefined){
      var saborpadrao = dados.sabores[0];
      var tamanhopadrao = dados.tamanhos[0];
      var cntsaborestroca = dados.sabores_troca.length;
      
      if(cntsaborestroca> 0){
        var addtrc = true;
        for(var tu=0; tu<cntsaborestroca; tu++){
            if(tamanhopadrao != null && tamanhopadrao != undefined){
                if(saborpadrao == dados.sabores_troca[tu].ID && tamanhopadrao.ID == dados.sabores_troca[tu].TAMANHO){
                    addtrc = false;
                    tu = cntsaborestroca;
                }
            }else{
                if(saborpadrao == dados.sabores_troca[tu].ID){
                    addtrc = false;
                    tu = cntsaborestroca;
                }
            }
        }
        if(addtrc === true){
            var otmhos = (dados.tamanhos != undefined && dados.tamanhos != false && dados.tamanhos.length>0)? dados.tamanhos[0].ID : null;
            
            dados.sabores_troca[cntsaborestroca] = {
                ID : dados.sabores[0],
                VALOR : 0,
                QTD : dados.quantidade,
                TAMANHO : otmhos
            };
            
        }
      }
      cntsaborestroca = dados.sabores_troca.length;
      
      if(cntsaborestroca> 0){
        let lista_itens_troca = [];

        for (var tu = 0; tu < cntsaborestroca; tu++) {
          for (var y = 0; y < contlistasabores; y++) {
            if (sabores_itens[y].sabor_id == dados.sabores_troca[tu].ID) {
              sabores_itens[y].qtd = dados.sabores_troca[tu].QTD;
              sabores_itens[y].tamanho = dados.sabores_troca[tu].TAMANHO;
              sabores_itens[y].valor = dados.sabores_troca[tu].VALOR
              lista_itens_troca.push(sabores_itens[y])
            }
          }
        }

        lista_itens_troca = ordenaListaProdutoSimplesPromosDesktop(dados.sessao_tipoordenacao, lista_itens_troca);
        for(let y = 0; y < lista_itens_troca.length; y++){
          var idsabor = lista_itens_troca[y].sabor_id;
          var otamanho = lista_itens_troca[y].tamanho;
          var qtdx = lista_itens_troca[y].qtd;
          var valplus = parseFloat(lista_itens_troca[y].VALOR);
          var nomedotamanho = "";
          var strvalorplus = (valplus>0)? " R$+"+parseReal(valplus) : "";
          var codtamaho = "";
          
          var dadostroca = {
              combo_hash : hashcombo,
              item_hash : ddhash,
              item_cod : codconf,
              prod_sabor : idsabor,
              prod_tamanho : otamanho
          };
          
          var nomefoto = lista_itens_troca[y].sabor_fotonome;
          var idfoto = lista_itens_troca[y].sabor_fotoid;
          var nomesabor = lista_itens_troca[y].sabor_nome;
          var listaingreds = lista_itens_troca[y].sabor_descricao;

          let tag_prod = "";
          let tag_prod_color = "#ff0000";
    
          if(lista_itens_troca[y]["sabor_tag"]){
            tag_prod = lista_itens_troca[y]["sabor_tag"]; 
            tag_prod_color = lista_itens_troca[y]["sabor_tagcor"];
          }
      
          let htmlTagProd = tag_prod != "" ? `<span class='tag_prod' style='background-color:${tag_prod_color}'>${tag_prod}</span>` : ""

          if(lista_itens_troca[y].sabor_precostamanhos != undefined && lista_itens_troca[y].sabor_precostamanhos.length>0){
            listaingreds = get_strListaIngred(lista_itens_troca[y].sabor_ingredientes);

            var qtdtamsab = lista_itens_troca[y].sabor_precostamanhos.length;
            for(var t=0;t<qtdtamsab;t++){
                if(otamanho == lista_itens_troca[y].sabor_precostamanhos[t].sabor_precotamanhos_codtamanho){
                    codtamaho = otamanho;
                    nomedotamanho = " ("+lista_itens_troca[y].sabor_precostamanhos[t].sabor_precotamanhos_nometamanho+") ";
                }
            }
          }

          if( (codtamaho == null && otamanho == null) || (codtamaho !== null && otamanho !== null) ){       
            if(lista_itens_troca[y].sabor_sessao_controlarestoque === 'S' && parseInt(lista_itens_troca[y].sabor_estoque) <= 0) {
              htmcont +=      "<li class='itensdelistasabores clicktrocardeitem item_indisponivel' data-dadostroca=''>";
            } else {
              htmcont +=      "<li class='itensdelistasabores clicktrocardeitem' data-dadostroca='"+ JSON.stringify(dadostroca) +"'>";
            }                
            htmcont +=         "<div class='fotoimglistasabor'>"
                +                   "<img src='"+urlsfiles.imagens+"produtos/"+idfoto+"/60/"+nomefoto+"' />"
                +               "</div>"
                +               `<span class='nomesaborlistasabores'>${qtdx} UND. ${nomesabor}${nomedotamanho} ${strvalorplus}<small class='precosaborlistasabores'></small></span>`
                +               "<p class='descingredienteslistasabores'>"+listaingreds+"</p>"
                +               htmlTagProd
                +           "</li>";  
          }
        } 
      }
    }
    
    var htmcontbusca = "<li class='itensdelistasaboresbusca'>"
    +               "<input type='text' class='buscarsabor' placeholder='Buscar Sabor' />"
    +           "</li>";
    var htmcontm ="<div class='listadesaboresescolher'>"
            +        "<div class='nano'>"
            //+           "<span class='titulolistasabores "+codtarget+"'>"+nomesessao+"</span>"                    
            +           "<span class='titulolistasabores'><img src='"+urlsfiles.media+vsao+"/img/fechar_side_esq.png' class='close_sidemenu_esq close_sidemenu_sabortroca'/>Trocar por...</span>"                    
            +           "<ul class='listacomsabores nano-content'>"+htmcontbusca+htmcont+"</ul>"
            +        "</div>"
            +    "</div>";
    
    $(".cont_abascombo").find(".listadesaboresescolher").remove();
    show_listaSabores_comb();
    $(".cont_abascombo").append(htmcontm);
    $(".nano").nanoScroller();
    
}


function trocarItem(dados){
    
    $.ajax({
        method: "POST",
        url: "/exec/montadoritem/trocaritemcombinado/",
        data: dados,
        dataType: "json"
    }).done(function( msg ) {
        if(msg.res === true){
            /*$("#montDorCombo").modal("hide"); 
            get_resumoPedido();
            $(".fechar_modal").show();
            showMsgItemAdd();*/
            
        
            //reendCorpoCombinado(msg.dados.itens, msg.hash);
            reendInfoCombo(msg.dados,msg.hash);
        }else if(msg.res === false){
            
        }else{
            //console.log("Falha na execução");
        }
        //alert("jszvnjzs");
    }); 
    
}

function reendListaItemSimples_combinado(dados){
  var targetaba = "";
  
  var sabores = dados.sabores;
  var qtd = dados.quantidade;
  var qtdtamanhos = dados.tamanhos.length;
  
  var tamanhos = (qtdtamanhos > 0)? dados.tamanhos : false;
  
  var htmlitemsimples = "";
  
  var cntsabores = sabores.length;
  var cntitemsabores = sabores_itens.length;
  var selectitem ="";
  var itensescolhidos = [];
  var cntitem = 0;
  
  var codsaborx = 0;
  var codtamanhox = null;
  var qtdsb_troca = 0;
  if(dados.itensescolhidos != undefined && dados.itensescolhidos.length > 0){
    itensescolhidos = dados.itensescolhidos;
    cntitem = itensescolhidos.length;
    try {
        qtdsb_troca = dados.sabores_troca.length;
    } catch (errorsabtroca) {
        qtdsb_troca = false;
    }
    
    codsaborx = itensescolhidos[0].item;
    codtamanhox = itensescolhidos[0].tamanho;
    qtd = itensescolhidos[0].qtd;
  }

  let sabores_troca =  dados.sabores_troca;
  let item_unico = false;

  if(Array.isArray(sabores_troca) && sabores_troca.length == 1 && dados.sabores[0] == sabores_troca[0]["ID"]){
    item_unico = true;
  }
  
  for(var y=0;y<cntitemsabores; y++){            
    var cdsabor = sabores_itens[y].sabor_id;
    if(cdsabor == codsaborx){
      var cdtipo = sabores_itens[y].sabor_sessaoid;
      var nomeiitem = sabores_itens[y].sabor_nome;
      var fotonomeitem = sabores_itens[y].sabor_fotonome;
      var fotoiditem = sabores_itens[y].sabor_fotoid;
      var caminhofoto = ""+urlsfiles.imagens+"produtos/"+fotoiditem+"/150/"+fotonomeitem;
      let controlar_estoque = sabores_itens[y].sabor_sessao_controlarestoque;
      let estoque = sabores_itens[y].sabor_estoque;
      let tag_prod = "";
      let tag_prod_color = "#ff0000";

      if(sabores_itens[y]["sabor_tag"]){
        tag_prod = sabores_itens[y]["sabor_tag"]; 
        tag_prod_color = sabores_itens[y]["sabor_tagcor"];
      }
  
      let htmlTagProd = tag_prod != "" ? `<span class='tag_prod' style='background-color:${tag_prod_color}'>${tag_prod}</span>` : ""
      
      var qtdunid = (qtd==1)? "<p>1 unidade</p>" : "<p>"+qtd+" unidades</p>";
      
      if(codtamanhox !== null){
        
        var tamanhossabor = sabores_itens[y].sabor_precostamanhos.length;
        var idtamth = codtamanhox;
        for(var sh=0; sh<tamanhossabor; sh++){
            var tmsh = sabores_itens[y].sabor_precostamanhos[sh].sabor_precotamanhos_codtamanho;
            if(tmsh == idtamth){
                
                
                var nometm = sabores_itens[y].sabor_precostamanhos[sh].sabor_precotamanhos_nometamanho;
                
                htmlitemsimples += "<div class='item_simp_comb "+targetaba+"' data-target-combo='"+targetaba+"' data-allconf='"+JSON.stringify(dados)+"' >"
                    +       htmlTagProd
                    +       "<img src='"+caminhofoto+"' alt='"+nomeiitem+"' width='110'/>"
                    +       "<p>"+nomeiitem+" ("+nometm+")</p>"
                    +       qtdunid;
                if(qtdsb_troca>1 || qtdsb_troca===false){
                    htmlitemsimples += "<a href='#' title='Trocar item' class='btn_sel_item trocarmeuitem "+targetaba+"'  data-target-combo='"+targetaba+"' data-codtam='"+idtamth+"' data-codsabor='"+cdsabor+"' data-codtipo='"+cdtipo+"' >Trocar item</a>";
                }
                htmlitemsimples += "</div>";
            }
        }                            
                                  
      }else{
        if(controlar_estoque === 'S' && estoque <= 0) {
          htmlitemsimples += "<div class='item_simp_comb "+targetaba+" item_indisponivel' data-target-combo='"+targetaba+"' data-allconf='"+JSON.stringify(dados)+"' >"
        } else {
          htmlitemsimples += "<div class='item_simp_comb "+targetaba+"' data-target-combo='"+targetaba+"' data-allconf='"+JSON.stringify(dados)+"' >"
        }
        htmlitemsimples +=  "<img src='"+caminhofoto+"' alt='"+nomeiitem+"' width='110'/>"
                +       htmlTagProd
                +       "<p>"+nomeiitem+"</p>"
                +       qtdunid;
                if((qtdsb_troca == 1 && item_unico == false) || qtdsb_troca > 1 || qtdsb_troca === false){
                  if(controlar_estoque === 'S' && estoque <= 0) {
                    htmlitemsimples += "<a href='#' title='Trocar item' class='btn_sel_item trocarmeuitem"+targetaba+" txt_indisponivel'  data-target-combo='"+targetaba+"' data-codtam='false' data-codsabor='"+cdsabor+"' data-codtipo='"+cdtipo+"' >Trocar item</a>";
                  } else {
                    htmlitemsimples += "<a href='#' title='Trocar item' class='btn_sel_item trocarmeuitem  "+targetaba+"'  data-target-combo='"+targetaba+"' data-codtam='false' data-codsabor='"+cdsabor+"' data-codtipo='"+cdtipo+"' >Trocar item</a>";
                  }
                }
                htmlitemsimples += "</div>";
      }       
    }
  }   
  return htmlitemsimples;
}
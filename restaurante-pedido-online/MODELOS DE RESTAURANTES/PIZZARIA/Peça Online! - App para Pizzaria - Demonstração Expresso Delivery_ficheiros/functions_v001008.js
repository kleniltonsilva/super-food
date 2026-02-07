
/* 
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */

function alinhaHeaderFooter(modal){
    var estrut = modal.find(".estruturamodal_");
    if(estrut.hasClass("header-sim_")){
        var headmd = modal.find(".headermodal_");
        var height_header = headmd.height();
        $(".estruturamodal_").css("padding-top","160px"); /**HUDSON**/
    }
    
    if(estrut.hasClass("footer-sim_")){
        var footermd = modal.find(".footermodal_");
        var height_footer = footermd.height();
        height_footer = height_footer-3;
        $(".estruturamodal_").css("padding-bottom",height_footer+"px");
    }
}

function rendPromocaoAtiva(){
    let cancelapromocao = false;
    $("#promocao_nomePromocao").text(promocaomontando.promocao_nome);
    $("#promocao_descricaoPromocao").text(promocaomontando.promocao_descricao);
    
    var codabaclickar = [];
    
    var html_liaba = "";
    var html_divlistas = "";
    
    var primeiraaba = null;
    var dados_itensselecpromo = {codpromo : null, codpromoacm : null, itens : [] };
    var cnt_qtditempremio = promocaomontando.promocao_itenspremios.length;
    let array_cod_abas = [];

    for(var d=0; d<cnt_qtditempremio; d++){
        dados_itensselecpromo.codpromo = promocaomontando.promocao_id;
        dados_itensselecpromo.codpromoacm = promocaomontando.promocao_idacm;
        var confiditem = promocaomontando.promocao_itenspremios[d].confitem;
        var sessao = get_dadosSessao(confiditem.tipo);
        if(sessao == false || sessao.indisponivel_turno){
          cancelapromocao = true;
          break;
        }
        
        var tamanho = get_tamanho_dados(confiditem.tamanho);
        var borda = get_borda_dados(confiditem.borda, confiditem.tamanho);
        var massa = get_massa_dados(confiditem.massa, confiditem.tamanho);
        var sabores = get_nomes_sabores(confiditem.sabor, confiditem.tamanho);
        var cntsa = sabores.length;
        qtd_itens = cntsa;
        //console.log(sabores);
        
        if(cntsa == 0){
            cancelapromocao = true;
        }
        
        var tamanhonome = "";
        var nome = "";
        if(tamanho !== false){
            tamanhonome+= tamanho.tamanho_nome + " de ";
        }if(massa !== false){
            nome+= " + " + massa.massa_nome;
        }if(borda !== false){
            nome+= " + " + borda.borda_nome;
        }
        var codaba = gerarValor(8,true,true);
        array_cod_abas.push(codaba);
        primeiraaba = (primeiraaba==null)? codaba : primeiraaba;
        dados_itensselecpromo.itens[d] = {
			codrefpromo : codaba, 
			codrefitem : null, 
			precoitem : 0, 
			hashitem : promocaomontando.promocao_itenspremios[d].coditem
		};
        var abapromoatv = (d==0)? " abaprmactive " : "";
        html_liaba +="<li class='clk_aba_promocompreganhe "+abapromoatv+"' data-codaba='"+codaba+"'>"+sessao.sessao_nome+"</li>";
        
        html_divlistas += "<div class='lista_itens_aba aba_"+codaba+"'>";
        if(cntsa === 1){
            var cntmumck = codabaclickar.length;            
            codabaclickar[cntmumck] = codaba+"";
        }
        for(var te=0; te<cntsa; te++){
            var fnome = tamanhonome + sabores[te].sabor_nome + nome;
            var dadositens = html_itemselecionarPromo_cg(codaba, fnome, sabores[te]);
            if(dadositens !== false){
              html_divlistas += dadositens;
            }
        }
        html_divlistas+="</div>";        
    }
    
    $(".abasitenspromo").html(html_liaba);
    $("#lista_itenspromocao").html(html_divlistas);
    $("#lista_itenspromocao").data("itensselecionados",dados_itensselecpromo);
    $(".lista_itens_aba").hide();
    $(".aba_"+primeiraaba).show();
    
    var cntclickpromo = codabaclickar.length;
    if(cntclickpromo > 0){
        for(var i_ck = 0; i_ck < cntclickpromo; i_ck++){
            $("."+codabaclickar[i_ck]+".btn_sel_item.additempromo_cg").trigger("click");
        }
    }
    
    if(cancelapromocao == true || array_cod_abas.length < 1){
      Swal({
        type: "info",
        title: "Nenhum item disponível",
        html: 'No momento infelizmente nenhum desses itens estão disponíveis, a promoção será invalidada.',
        onClose: () => {
          rejeita_compreeganhe();
          $("#modalItensPromo").modal("hide");
          }
      }); 
      return;
    }

    array_cod_abas.forEach(function(element){
      let todos_itens = $(`.item_simp_comb[data-codrefpromo='${element}']`).length;
      let todos_itens_indisponiveis = $(`.item_indisponivel[data-codrefpromo='${element}']`).length;
      if(todos_itens == todos_itens_indisponiveis) {
        Swal({
          type: "info",
          title: "Nenhum item disponível",
          html: 'No momento infelizmente nenhum desses itens estão disponíveis, a promoção será invalidada.',
          onClose: () => {
            rejeita_compreeganhe();
            $("#modalItensPromo").modal("hide");
            }
        }); 
        return;
      }
    })

    if(cancelapromocao === true){
        $("#modalItensPromo").modal("hide");
        $("#modalQuestionPromo").modal("hide");
    }
    
}

function html_itemselecionarPromo_cg(codaba, nomesabor, dadossabor, preco){
    let foto = `${urlsfiles.imagens}produtos/${dadossabor.sabor_fotoid}/150/${dadossabor.sabor_fotonome}`;
    if (dadossabor.sabor_image){
      foto = `${urlsfiles.imagens}itens/${dadossabor.sabor_image}`;
    }

    if(dadossabor.sabor_sessao_controlarestoque === 'S' && parseInt(dadossabor.sabor_estoque) <= 0) {
      return '<div class="item_simp_comb zeroitem '+codaba+' item_indisponivel" data-codrefpromo="'+codaba+'">'
              +   '<img src="'+ foto +'" alt="'+nomesabor+'" width="110">'
              +   '<p>'+nomesabor+'</p>'
              +   '<a href="#" title="Selecionar" class="btn_sel_item  '+codaba+' txt_indisponivel">Indisponível</a>'
              +'</div>';
    } else {
      return '<div class="item_simp_comb zeroitem '+codaba+' " data-codrefpromo="'+codaba+'">'
              +   '<img src="'+ foto +'" alt="'+nomesabor+'" width="110">'
              +   '<p>'+nomesabor+'</p>'
              +   '<a href="#" title="Selecionar" class="btn_sel_item additempromo_cg '+codaba+'" data-codrefpromo="'+codaba+'" data-precoitem="'+dadossabor.sabor_precopromocao+'" data-codsabor="'+dadossabor.sabor_id+'" >Selecionar</a>'
              +'</div>';
    }
}

function set_promocaoCompreGanhe(dados){
  showLoading();
  $.ajax({
      method: "POST",
      url: "/exec/pedido/promocaocompreganhe",
      data: dados,
      dataType : "json"
  }).done(function( msg ) {
    hideLoading();
      if(msg.res === true){
          $('#modalItensPromo').modal("hide");            
          get_resumoPedido();    
          $("#add_promocao_cg").removeClass("ativo");
      } else {
        rejeita_compreeganhe();
        $('#modalItensPromo').modal("hide");
        Swal({
            type: 'warning',
            title: 'Oops..',
            html: 'Algo deu errado.<br/> A promoção será invalidada.<br/> Clique em Promoções Rejeitadas para tentar novamente.',
            onClose: () => {
                document.location.reload();
            }
        });
      }
  });
  hideLoading();
}

function check_itensPromocaoSelecionados(){
	var dados_promocg_atual = $("#lista_itenspromocao").data("itensselecionados");
	var precopromoescrt = "GRÁTIS";
	if(promocaomontando.promocao_tipodesconto == "porcentagem"){
		var vlpctg = promocaomontando.promocao_valordesconto;
		var total = 0;

		if(dados_promocg_atual.itens != undefined){
			var cnt_dadospromo = dados_promocg_atual.itens.length;
			for(var ds=0; ds<cnt_dadospromo; ds++){
				total += parseFloat(dados_promocg_atual.itens[ds].precoitem);
			}
			precopromoescrt = "R$ "+  parseReal(total * (1 - (vlpctg/100)) );
		}else{
			precopromoescrt = "";
		}
	}else if(promocaomontando.promocao_tipodesconto == "porapenas"){
		if(dados_promocg_atual.itens != undefined){
			var vlpctg = promocaomontando.promocao_valordesconto;
			precopromoescrt = "R$ "+  parseReal(vlpctg);
		}else{
			precopromoescrt = "";
		}
	}
	
	$(".realprecopromo").text(precopromoescrt);
    var cnt_dadospromo = dados_promocg_atual.itens.length;
    for(var ds=0; ds<cnt_dadospromo; ds++){
        if(null == dados_promocg_atual.itens[ds].codrefitem){
            return false;
        }
    }
    $("#add_promocao_cg").addClass("ativo");
	$('#add_promocao_cg').animateCss('tada');
}

function showMsgItemAdd(){
    $(".itemaddcionado").stop().fadeIn( 500 , function(){
        setTimeout(function(){
            $(".itemaddcionado").stop().fadeOut( 500 );
        },2000);
    });
}

function rejeita_compreeganhe(){
    var cnt_rej = promocoesRejeitadas.length;
    
    if( !in_array(promocaomontando.promocao_id, promocoesRejeitadas)){
      promocoesRejeitadas[cnt_rej] = clone(promocaomontando.promocao_id);
      
      var ywydvg = promocoesRejeitadas.join("and");
      setCookie("promocoesrejeitadas", ywydvg);
      if(promocoesRejeitadas.length>0){
        $(".qtdpromorej").show();
        $(".qtdpromorej").text("Promoções rejeitadas: "+promocoesRejeitadas.length+" - clique aqui para liberar");
      }else{
        $(".qtdpromorej").hide();
      }
      rendPromocaoRT();
    }
}

$(document).ready(function(){
    
    $(document).on("click",".openCombo",function(e){
        const dadosmontcombo = $(this).data("dadoscombo");    
        if(dadosmontcombo!==false && dadosmontcombo!==undefined){
            buscaConfComboMontador(dadosmontcombo,"combo");
        }else{
            $("#montDorCombo").modal("hide");
            Swal({
                type: 'info',
                title: 'Oops',
                text: 'Esse Combo Não é Válido para Hoje'
              });
        }
    });
    
    $(document).on("click",".openCombinado",function(e){
        var dadosmontcombo = $(this).data("dadoscombo");    
        if(dadosmontcombo!==false && dadosmontcombo!==undefined){
            buscaConfComboMontador(dadosmontcombo,"combinado");
        }else{
            Swal({
                type: 'info',
                title: 'Oops',
                text: 'Esse Combo Não é Válido para Hoje'
              });
        }
    });
    
    $('#modalQuestionPromo').on('shown.bs.modal', function() {
        alinhaHeaderFooter($(this));
    });
    
    $('#modalItensPromo').on('shown.bs.modal', function() {
        alinhaHeaderFooter($(this));       
        rendPromocaoAtiva();
    });
    
    $(document).on("click", ".additempromo_cg", function(e){
        var codref = $(this).data("codrefpromo");
        var codsabor = $(this).data("codsabor");
		var precoitem = $(this).data("precoitem");
        var dados_promocg_atual = $("#lista_itenspromocao").data("itensselecionados");
        var cnt_dadospromo = dados_promocg_atual.itens.length;
        for(var ds=0; ds<cnt_dadospromo; ds++){
            if(codref == dados_promocg_atual.itens[ds].codrefpromo){
                dados_promocg_atual.itens[ds].codrefitem = codsabor;
				dados_promocg_atual.itens[ds].precoitem = precoitem;
                $("#lista_itenspromocao").data("itensselecionados",dados_promocg_atual);
                $(".item_simp_comb."+codref).removeClass("selecionado");
                var parent = $(this).parent();
                parent.addClass("selecionado");                
            }
        }
        check_itensPromocaoSelecionados();
    });
    
    $("#add_promocao_cg").click(function(e){
        if($(this).hasClass("ativo")){
            var dados_promocg = $("#lista_itenspromocao").data("itensselecionados");
            set_promocaoCompreGanhe(dados_promocg);
        }
    });
	
	$(document).on("click",".qtdpromorej", function(e){
		promocoesRejeitadas = [];
		var ywydvg = promocoesRejeitadas.join("and");
		setCookie("promocoesrejeitadas", ywydvg);
		rendPromocaoRT();
	});
        
    $(document).on("click",".clk_aba_promocompreganhe", function(){
        if( !($(this).hasClass("abaprmactive")) ){
            $(".clk_aba_promocompreganhe").removeClass("abaprmactive");
            $(this).addClass("abaprmactive");
            var codsessao = $(this).data("codaba");
            $(".lista_itens_aba").hide();
            $(".aba_"+codsessao).show();
        }
    });
       
    $(document).on("click","#btn_finalizar_pedido",function(e){
      if (pauseDeliveryOnline["status"]) {
        const start = new Date(pauseDeliveryOnline["date"]);
        const end = new Date(start.getTime() + pauseDeliveryOnline["time"] * 60 * 1000);
      
        const timeToOpenInMs = (end.getTime() - new Date().getTime());
        let timeToOpenInMinutes = Math.round(timeToOpenInMs / 1000 / 60);
        if (timeToOpenInMinutes == -1) timeToOpenInMinutes = 1;
        const elementTimeToOpen = timeToOpenInMinutes > 1 ? `${timeToOpenInMinutes} minutos` : `${timeToOpenInMinutes} minuto`;
      
  
        Swal({
          title: "Já voltamos!",
          html: `Estamos fazendo uma pausa rápida.<br>Em <span id='time-to-open-pause-delivery'>${elementTimeToOpen}</span>, voltaremos a aceitar pedidos!`,
          type: "info"                  
        }); 
  
        return
      }
      
      document.location.href = "/finalizar-pedido/";
    });
        
    /*
     * Click botão adicionar item com personalização
     */
    $(document).on("click", ".clk_botao_itempersonal", function(e){
      const dados = $(this).data("dadositem");
      let mtdr = $(this).data("montador");
      if (mtdr == "montador-slider") mtdr = null;
        
      add_item(dados, mtdr);
    });
    
    //
    $(document).on("click", ".deletar_item", function(e){
        var prt = $(this).parent();
        var dados = prt.data("dadosalteracao");        
        acoesItemPedido(dados,"deletar");
    });

    $(document).on("click", ".deletar_premio", function(e){
        var key = $(this).data("key");
        $.ajax({
            method: "POST",
            url: "/exec/pedido/fidelidade_deletarpremio",
            data: {
                key: key
            },
            dataType : "json"
        }).done(function( msg ) {
            if(msg.res === true){ 

                get_resumoPedido();            

            }
        });
    });

    $(document).on("click", ".addmais_combo", function(e){
        const prt   = $(this).parent();
        const dados = prt.data("dadosalteracao");        
        actionsCombo(dados, 'aumentar');
    });
    $(document).on("click", ".addmenos_combo", function(e){
        const prt   = $(this).parent();
        const dados = prt.data("dadosalteracao");        
        const qtd   = $(this).next('input').val();
        
        if(qtd > 1){
            actionsCombo(dados, 'diminuir');
            return true;
        }
        Swal({
            title: 'Remover Combo do Pedido?',
            text: 'Deseja remover esse combo do seu pedido?',
            type: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3e9a00',
            cancelButtonColor: '#3085d6',
            cancelButtonText: 'Não',
            confirmButtonText: 'Sim, Remover Item!',
            allowOutsideClick: false,
            allowEscapeKey: false
        }).then(function(result) {
            if (result.value) {
                actionsCombo(dados, 'deletar');
            }
        });
    });
    
    $(document).on("click", ".deletarcombo_item", function(e){
        var prt = $(this).parent();
        const dados = prt.find('.qtd_item').data("dadosalteracao");        
        actionsCombo(dados,"deletar");
    });
    
    $(document).on("click", ".addmais_item", function(e){
        var prt = $(this).parent();
        var dados = prt.data("dadosalteracao");        
        acoesItemPedido(dados,"aumentar");
    });
    $(document).on("click", ".addmenos_item", function(e){
        var prt = $(this).parent();
        var dados = prt.data("dadosalteracao");        
        
        var qtd = $(this).next('input').val();
        
        if(qtd > 1){
            acoesItemPedido(dados,"diminuir");
        }
        else{
            Swal({
                title: 'Remover Item do Pedido?',
                text: 'Deseja remover esse item do seu pedido?',
                type: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#3e9a00',
                cancelButtonColor: '#3085d6',
                cancelButtonText: 'Não',
                confirmButtonText: 'Sim, Remover Item!',
                allowOutsideClick: false,
                allowEscapeKey: false
            }).then(function(result) {
                if (result.value) {
                    acoesItemPedido(dados,"deletar");
                }
            });
        }
    });
    
    $(document).on("click", ".editar_combopedido", function(e) {
        const prt = $(this).parent();
        const dados = prt.find('.qtd_item').data('dadosalteracao');
        if (dados === undefined || dados === null) {
            console.error('Faltam os dados para edição do combo (em "dadosalteracao").');
            return false;
        }
        actionsCombo(dados, 'editar');
		$(".fechar_modal").hide();
    });

    $(document).on("click", ".editar_itempedido", function(e){
        var prt = $(this);
        var dados = prt.data("dadosalteracao");        
        acoesItemPedido(dados,"editar");
    });
    
    $(".linksess").click(function(e){
        $(".listamenucardapio").removeClass("ativo");
        $(this).parent().addClass("ativo");
        var valor_sessao = $(this).data("sessao");
        $("#grupo_sessao_"+valor_sessao).trigger("click");

        if( !$("#grupo_sessao_"+valor_sessao).hasClass("showsessao") ){
            $(".item_e").removeClass("showsessao");
           $("#grupo_sessao_"+valor_sessao).addClass("showsessao");
        }

        if($("#selccc_"+valor_sessao).length>0){
            $("#selccc_"+valor_sessao).trigger("change");
        }
        if($(".abbb_"+valor_sessao).length>0){
            $(".abbb_"+valor_sessao+".abaativa").trigger("click");
        }
		$("#grupo_sessao_"+valor_sessao+" .listade_produtos").css("padding-top",($("#grupo_sessao_"+valor_sessao+" .lista_deabas").height()-25)+"px");
    });

    $(document).on("click",".aba_sessao", function(e){
        $(".msg_naohaitenstc").hide();
        var tipo = $(this).data("tipo");
        var sessao_th = $(this).data("codsessao");
        var cod = $(this).data("cod");

        $(".abbb_"+sessao_th).removeClass("abaativa");
        $(this).addClass("abaativa");

        var selec_x = false;
        if($("#selccc_"+sessao_th).length>0){
            selec_x = $("#selccc_"+sessao_th).val();
        }
        $(".clk_sessao_x"+sessao_th).hide();
        if(tipo == "categoria"){
            if(selec_x != false){
                $(".clk_tamanho_x"+selec_x+".clk_categoria_x"+cod).show();
                if($(".clk_tamanho_x"+selec_x+".clk_categoria_x"+cod).length == 0){
                    $(".msg_naohaitenstc").show();
                }
            }else{
                $(".clk_categoria_x"+cod).show();
                if($(".clk_categoria_x"+cod).length == 0){
                    $(".msg_naohaitenstc").show();
                }
            }
        }else if(tipo == "tamanho"){
            if(selec_x != false){
                $(".clk_tamanho_x"+cod+".clk_categoria_x"+selec_x).show();
                if($(".clk_tamanho_x"+cod+".clk_categoria_x"+selec_x).length == 0){
                    $(".msg_naohaitenstc").show();
                }
            }else{
                $(".clk_tamanho_x"+cod).show();
                if($(".clk_tamanho_x"+cod).length == 0){
                    $(".msg_naohaitenstc").show();
                }
            }
        }
    });

    $(document).on("change", ".select_sessao", function(e){
        $(".msg_naohaitenstc").hide();
        var tipo = $(this).data("tipo");
        var sessao_th = $(this).data("codsessao");
        var cod = $(this).val();

        var selec_x = false;
        if($(".abbb_"+sessao_th+".abaativa").length>0){
            selec_x = $(".abbb_"+sessao_th+".abaativa").data("cod");

        }
        $(".clk_sessao_x"+sessao_th).hide();
        if(tipo == "categoria"){
            if(selec_x != false){
                $(".clk_tamanho_x"+selec_x+".clk_categoria_x"+cod).show();
                
                if($(".clk_tamanho_x"+selec_x+".clk_categoria_x"+cod).length == 0){
                    $(".msg_naohaitenstc").show();
                }
                
            }else{
                $(".clk_categoria_x"+cod).show();
                if($(".clk_categoria_x"+cod).length == 0){
                    $(".msg_naohaitenstc").show();
                }
            }
        }else if(tipo == "tamanho"){
            if(selec_x != false){
                $(".clk_tamanho_x"+cod+".clk_categoria_x"+selec_x).show();
                if($(".clk_tamanho_x"+cod+".clk_categoria_x"+selec_x).length == 0){
                    $(".msg_naohaitenstc").show();
                }
            }else{
                $(".clk_tamanho_x"+cod).show();
                if($(".clk_tamanho_x"+cod).length == 0){
                    $(".msg_naohaitenstc").show();
                }
            }
        }
    });    
});

function acoesItemPedido(dados,acao){
    var dadosacao = {
        dados : dados,
        acao : acao
    };
    showLoading();
    $.ajax({
        method: "POST",
        url: "/exec/pedido/itempedido/",
        data: dadosacao,
        dataType : "json"
    }).done(function( msg ) {
      hideLoading();
        if(msg.res === true){            
            if(msg.dados != undefined){
                if(msg.dados.acao === "editar" || msg.dados.acao === "itemInEdition"){
                    if(msg.dados.redirect != undefined && msg.dados.redirect != false){
                        document.location.href = msg.dados.redirect;
                    }else{
                        var codgerado = gerarValor(8,true,true);                    
                        openModalItem_editar(codgerado);
                        setTimeout(function(){
                            $("#montDor").modal("show");
                            compositionsItemMontador.compositions = [];
                            compositionsItemMontador.add = [];
                            peencheDadosRetorno(msg,codgerado);
                            peencheMontadorItem(codgerado);
                        },200);
                    }
                }
              }            

              if (acao == 'diminuir' || acao === 'deletar') {
                let elementsUpsell = $('.inputUpsell.upsell_additemcart');
                for (let i = 0; i < elementsUpsell.length; i++) {
                  const element = $(elementsUpsell[i]);
                  if (element.data('upsell-itemid') == dados['skeycod']) {
                    let currentValue = parseInt(element.html());
                    if (currentValue < 1) {
                      get_resumoPedido();            
                      break;
                    }
                    element.html(currentValue -1)
                    break;
                  }
                }
              }
            get_resumoPedido();   
            
            return;
        }

        Swal({
          title: "Ocorreu um Erro",
          html: msg.msg,
          type: "error"                  
        }); 
    });
}

function criaMsgCombosDisponivelApenasBalcão(combo, forma_entrega){
  let resposta = "<div style='text-align: left;padding-left:15px;'>";
  resposta = `<span style="text-align: left; display:block;">O combo abaixo é válidos apenas para ${forma_entrega}:</span>`;
  resposta += `<li><strong>${combo.combo_nome}</strong></li>`;
  resposta += '</div>';
  resposta += '<span style="text-align: left; display:block;">Remova o combo do pedido para prosseguir.</span>';
  return resposta;
}

function criaMsgCombosIndisponiveisFormaEntrega(dados, finalizar_pedido = false){
  let combos = "<div style='text-align: left;padding-left:15px;'>";
  for(let i = 0; i < dados.length; i++) {
    combos += `<li><strong>${dados[i]['combo'].combo_nome}</strong></li>`;
  }

  let textTypeDelivery = "";
  for (let i = 0; i < dados[0]['typeDelivery'].length; i++) {
    switch (dados[0]['typeDelivery'][i]) {
      case 'E':
        textTypeDelivery += "Entrega, ";
        break;
      case 'R':
        textTypeDelivery += "Retirada, ";
        break;
      case 'C':
        textTypeDelivery += "Consumir no Local"
    }
  }

  textTypeDelivery = textTypeDelivery.replace(/,\s+$/, '')
  textTypeDelivery = textTypeDelivery.replace(/,$/, '')
  textTypeDelivery = textTypeDelivery.replace(/,([^,]*)$/,' e'+'$1');
  
  let resposta = `<span style="text-align: left; display:block;">Os combos abaixo são válidos apenas para ${textTypeDelivery}:</span>`;
  resposta += `${combos}`;
  resposta += '</div>';
  
  if(finalizar_pedido == true) {
    resposta += '<span style="text-align: left; display:block;">Remova os combos do pedido ou altere a forma de entrega.</span>'    
  } else {
    resposta += '<span style="text-align: left; display:block;">Remova os combos do pedido e depois altere a forma de entrega.</span>'
  }
  return resposta;
}

function removerComboPedido(dados){
    $.ajax({
        method: "POST",
        url: "/exec/pedido/removercombo",
        data: dados,
        dataType : "json"
    }).done(function( msg ) {
        if(msg.res === true){ 
            get_resumoPedido();            
        }
    });
}

function add_item(dados, mdtr){
    const cookieUpsell = Cookies.get('openUpsellED');
    if (cookieUpsell && cookieUpsell != dados.codtipo) {
        Cookies.remove('openUpsellED');
    }
    showLoading();
    $.ajax({
        method: "POST",
        url: "/exec/pedido/adicionaritem",
        data: dados,
        dataType : "json"
    }).done(function( msg ) {
      hideLoading();
        if(msg.res === true){
            resetArrayCompositionsItem();
            if(fbp_configurado == true && dados != undefined && dados != null){
                fbq('track', 'AddToCart', {
                    content_name: dados.nomeitem, 
                    content_category: dados.tiponome,
                    content_ids: [dados.coditem],
                    content_type: 'product',
                    value: dados.precoitem,
                    currency: 'BRL'
                },
                {
                  eventID: facebookEventID
                }
              );
            }

            if(tiktokpixel_configurado == true && dados != undefined && dados != null){
              ttq.track('AddToCart', {
                content_name: dados.nomeitem, 
                value: dados.precoitem,
                content_category: dados.tiponome,
                content_id: [dados.coditem],
                content_type: 'product',
                currency: 'BRL'
              });
            }
        
            if(msg.dados !== false){
                if(mdtr != false && mdtr != undefined){
                    document.location.href = msg.dados.redirect;
                }else{
                    var codgerado = gerarValor(8,true,true);
                    rendAbrirItem(msg, codgerado);
                    $("#montDor").modal("show");

                    if(msg.htmlItemsUpsell) {
                      setTimeout(function(e){
                        addUpsellMontadorPadraoDesktop(msg.htmlItemsUpsell, dados.codtipo)
                      }, 200);
                    }
                }
            }else{
                if(msg.htmlItemsUpsell) {
                    getModalUpsell(msg.htmlItemsUpsell, dados.codtipo, false, true)
                } else {
                  showMsgItemAdd();
                }
                get_resumoPedido();
            }
        }else if(msg.res === false){            
            if(msg.indisponibilidade_turno && msg.indisponibilidade_turno == true && msg.turnos_sessao && msg.turnos_sessao.length > 0) {
              Swal({
                  title: "Produto Indisponível",
                  html: geraMensagemDisponibilidadePorTurno(msg.turnos_sessao),
                  type: "warning"                  
              }); 
            }
        }
    });
}

function geraMensagemDisponibilidadePorTurno(dados, message = "Não trabalhamos com esse produto no momento."){
  let html = `<p>${message}`;
  if(Array.isArray(dados) === false || dados.length < 1){
    html += '</p>'
    return html;
  }

  html += ' Confira a disponibilidade abaixo:</p>';
  html += '<ul>'
  for(let i = 0; i < dados.length; i++){
    if(Array.isArray(dados[i].turno_diasdasemana) === false || dados[i].turno_diasdasemana < 1){
      continue;
    }
    for(let y = 0; y < dados[i].turno_diasdasemana.length; y++){
      html += `<li><strong style="text-transform: capitalize;">${dados[i].turno_diasdasemana[y]}</strong> das ${dados[i].turno_horainicial}h às ${dados[i].turno_horafinal}h</li>`;
    }
  }
  html += '</ul>';
  return html;
}

function get_resumoPedido(){
    $.ajax({
        method: "POST",
        url: "/exec/pedido/pedido",
        data: { acao : "resumo" },
        dataType : "json"
    }).done(function( msg ) {
        if(msg.res === true){ 
            resumo = msg.resumo;
            promocoesAtivas = msg.promocaoAtiva;
            renderizaResumo();
            //rendResumoNew();
            rendPromocaoRT();

            if (msg?.promoDeliveryFee && typeof renderPercentageToPromotionDeliveryFee == "function") {
              renderPercentageToPromotionDeliveryFee(msg.promoDeliveryFee)
            }
  
            if (msg?.promoBuyAndGet && typeof renderPercentageToPromotionBuyAndGet == "function") {
              renderPercentageToPromotionBuyAndGet(msg.promoBuyAndGet)
            }
        }else if(msg.res === false){            
            renderizaResumo();
        }
    });
}

function rendPromocaoRT(){
	$(".realprecopromo").text("");
  var cnt_promocao = promocoesAtivas.length;
  if(cnt_promocao > 0){
    for(var i=0; i<cnt_promocao; i++){			
      var thisPromo = promocoesAtivas[i];
      promocaomontando = thisPromo;
      showModalpromocao = true;                
      i=cnt_promocao;
      if(!promocaoRejeitada(thisPromo)){
        if ($("#modalItensPromo").is(':visible')) {
          $("#modalItensPromo").modal('hide');
        }

        if(thisPromo.promocao_tipodesconto == "gratis"){
          showPromocaoGratis(thisPromo);
        } else {
          showPromocaoComdesconto();
        }
      }else{
        if(is_array(promocoesRejeitadas)){
            var prmrjet = promocoesRejeitadas.length;
            if(prmrjet>0){
                $(".qtdpromorej").show();
                $(".qtdpromorej").text("Promoções rejeitadas: "+prmrjet+" - clique aqui para liberar");
            }else{
                $(".qtdpromorej").hide();
                $(".qtdpromorej").text("");
            }
        }
      }
    }
  }
}

function promocaoRejeitada(promo){
    
    var cnt_rej = promocoesRejeitadas.length;
    for(var i=0; i<cnt_rej; i++){
        if(promocoesRejeitadas[i] == promo.promocao_id){
            return true;
        }
    }
    return false;
}

function showPromocaoGratis(){
	
    $("#modalItensPromo").modal("show");
}

function showPromocaoComdesconto(){
    if(showModalpromocao){
        Swal({
          allowOutsideClick: false, 
          title: promocaomontando.promocao_nome,
          html: promocaomontando.promocao_descricao,
          showCancelButton: true,
          cancelButtonColor: '#d33',
          confirmButtonText: 'RESGATAR MINHA PROMOÇÃO',
          cancelButtonText: 'NÃO, OBRIGADO',
          allowEscapeKey: false
      }).then((result) => {
          if (result.value) { 
              $("#modalItensPromo").modal("show");
          } else {
              rejeita_compreeganhe();
          }
      });
    }
}

/*
 * Funções para renderizar resumo
 */
function renderizaResumo(){
    var htmlresumo = "<div class='car-sem-item'> <img src='"+imgCarrinho+"'> <img style='margin-top: 50px;' src='"+urlsfiles.media+vsao+"/img/seta-add-item.png'> </div>";
    var htmltotais = "";
    if(resumo != undefined){
        var itens = resumo.pedido_itens;
        if(itens != undefined && itens.length > 0){
            htmlresumo = "";
            htmltotais = gera_htmlResumoTotais();
            var cntitens = itens.length;
            for(var f=0; f<cntitens; f++){
                htmlresumo += gera_htmlItens_nw(itens[f]);
            }
        }
    }

    $("#cont_resumo").html(htmlresumo);
    $("#total-finaliza-ped").html(htmltotais);
    componentHandler.upgradeDom();

    if (window.location.href.indexOf('/finalizar-pedido') > -1) {
      $('#pedido_cupom').val(resumo?.pedido_codigocupom ?? '');
      $('.inputQuantityComboSummary').attr('disabled', true);
      $('.inputQuantityProductSummary').attr('disabled', true);
      
      const typeDelivery = resumo.pedido_formaentrega_cod;
      const totalOrder = parseFloat(resumo.pedido_totalitens);
      const cupomIgnoreMinimumOrder = resumo["pedido_cupomIgnoreMinimumOrder"] ?? 'N';
      if (cupomIgnoreMinimumOrder == 'N') {
        if(typeDelivery === "R" || typeDelivery === "C"){
          const minimumValueTakeout = parseFloat($('#minimumValueTakeout').val());
          if (totalOrder < minimumValueTakeout) {
            $('#btnpassaaregua').addClass('disabled').data("reason", `O seu pedido não atingiu o valor mínimo para retirar de R$ ${parseReal(minimumValueTakeout)}. <br/>Adicione mais itens ou altere a forma de entrega.`);
          } else {
            $('#btnpassaaregua').removeClass('disabled').removeAttr("data-reason");
          }
        }
        
        if (typeDelivery == 'E') {
          const minimumValueDelivery = parseFloat($('#minimumValueDelivery').val());
          if (totalOrder < minimumValueDelivery) {
            $('#btnpassaaregua').addClass('disabled');
            $('#btnpassaaregua').addClass('disabled').data("reason", `O seu pedido não atingiu o valor mínimo para entrega de R$ ${parseReal(minimumValueDelivery)}. <br/>Adicione mais itens ou altere a forma de entrega.`);
          } else {
            $('#btnpassaaregua').removeClass('disabled').removeAttr("data-reason");
          }
        }
      }
      else {
        $('#btnpassaaregua').removeClass('disabled').removeAttr("data-reason");
      }
    }
}

function gera_htmlResumoTotais(){
    var desconto = parseFloat(resumo.pedido_desconto);
    let descontoCupom = resumo.hasOwnProperty("pedido_cupomDesconto") && parseFloat(resumo.pedido_cupomDesconto) > 0 ? parseFloat(resumo.pedido_cupomDesconto) : 0;
    if (descontoCupom > 0) {
      desconto = desconto - descontoCupom;
    }
    descontoCupom = resumo.hasOwnProperty("pedido_descontoCupom") && parseFloat(resumo.pedido_descontoCupom) > 0 ? parseFloat(resumo.pedido_descontoCupom) : descontoCupom;
    
    var fretevalor = resumo.pedido_fretepor;
    var valorpedido = parseFloat(resumo.pedido_preco);
    const totalItems = resumo.pedido_itens.reduce((total, item) => total + parseFloat(item.item_preco * (parseInt(item.item_quantidade) + parseInt(item.qtd_combos))), 0);
    const paymentFee = resumo?.pedido_paymentFee ?? 0;
    
    var htmltotaisresumo = `
      <p class="txtdesconto_resumo">
        <span>Itens: R$ ${parseReal(totalItems)}</span>
      </p>
    `;
    
    if(fretevalor != null){		
      if (fretevalor > 0) {
        htmltotaisresumo += "<p class='txtdesconto_resumo'>"
              +        "<span class='txt_taxa'>+ Taxa de Entrega:</span>"
              +        "<span id='valtaxa'> R$ "+parseReal(fretevalor)+"</span>"
              +    "</p>";
      } else {
        htmltotaisresumo += "<p class='txtdesconto_resumo'>"
              +        "<span class='txt_taxa'>Entrega: Grátis</span>"
              +    "</p>";
      }
    }

    if(paymentFee > 0){		
		  htmltotaisresumo += "<p class='txtdesconto_resumo'>"
            +        "<span class='txt_taxa'>+ Acréscimo de Pagamento:</span>"
            +        "<span> R$ "+parseReal(paymentFee)+"</span>"
            +    "</p>";
    }

    if(desconto > 0){
		  htmltotaisresumo += "<p class='txtdesconto_resumo'>"
            +        "- Desconto: R$ "+parseReal(desconto)
            +    "</p>";	
    }

    if(descontoCupom > 0){
		  htmltotaisresumo += "<p class='txtdesconto_resumo'>"
            +        "- Cupom: R$ "+parseReal(descontoCupom)
            +    "</p>";	
    }
    
    htmltotaisresumo +=  "<p id='txttotal' class='preco-item-ped preco-itempizza-ped'>" /* style='margin-bottom: 15px;'*/
        +        "Valor Total do Pedido: R$ <span id='totalrs-ped'>"+parseReal(valorpedido)+"</span>"
        +    "</p>"
        +    "<button class='mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect mdl-button--accent' id='btn_finalizar_pedido' >"
        +        "<i class='material-icons'>check_circle</i> Finalizar Pedido"
        +    "<span class='mdl-button__ripple-container'><span class='mdl-ripple'></span></span></button>"
		+    "<span class='qtdpromorej'></span>";
    
    reendInfoCheckout();
    return htmltotaisresumo;
}

function reendInfoCheckout(){
    if($(".bl-taxa").length >0){
        var fretevalor = resumo.pedido_fretepor;
        var fretevalorde = resumo.pedido_fretede;
        
        if(fretevalor == null){
            $(".bl-taxa").text("Taxa de entrega: (calcular)");
        }else if(fretevalorde != undefined){
            try{
                fretevalorde = parseFloat(fretevalorde);
            }catch(eewe){
                fretevalorde = 0;
            }
            $(".bl-taxa").html("");
            $(".bl-taxa").text("Taxa de entrega:");
            if(fretevalorde >fretevalor){                
                $(".bl-taxa").append('<span class="preco_fretes"><span class="preco_de">de R$ '+parseReal(fretevalorde)+'</span><small>por R$ </small>'+parseReal(fretevalor)+'</span>');
            }else{
                $(".bl-taxa").append('<span class="preco_fretes">R$ '+parseReal(fretevalor)+'</span>');
            }
        }
    }
}

function gera_htmlItens(item){
    var htmlitem = "";
    var tipoitem = item.tipo;
    if(tipoitem === "combo"){
        htmlitem += gera_htmlCombo(item);
    }else if(tipoitem === "simples"){
        htmlitem += gera_htmlItemSimples(item);
    }else if(tipoitem === "composto"){
        htmlitem += gera_htmlItemComposto(item);
    }else if(tipoitem === "promocaocg"){
        htmlitem += gera_htmlPromocao_cg(item);
    }
    return htmlitem;        
}

function gera_htmlCombo(item){
    var combo_nome = item.nome;
    var combo_preco= parseReal(item.preco);
    var combo_economia = parseReal(item.economia);
    var dadosmanip = JSON.stringify(item.dadosalter);
    var itens = item.itens;
    var cntitens = itens.length;
    
    var htmeconomia = "";
    if( parseFloat(item.economia)>0 ){
        htmeconomia = "<p class='economia'><i class='material-icons'>thumb_up</i> Você economizou R$ "+combo_economia+"</p>";
    }
    var html = "<div class='combo'  data-dadosalteracao='"+dadosmanip+"'>"
        +    "<p class='tit_combo_resumo'>"+combo_nome+": R$ "+combo_preco+"</p>"
        +    htmeconomia;

    for(var t=0; t<cntitens;t++){
        html+=   "<div class='item_resumo_combo'>"
            +        "<div class='det_item_resumo'>"
            +            "<p class='nomeitem_resumo'>"+itens[t].nome.linha1+"</p>"
            +            "<p class='descitem_resumo'>"+itens[t].nome.linha2+"</p>"
            +        "</div>"
            +        "<div class='clear'></div>"
            +    "</div>";
    }
    
    html+=   "<button class='mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect   btn_excluircombo deletarcombo_item'><i class='material-icons'>delete</i> Excluir</button>"
        +    "<button class='mdl-button mdl-js-button mdl-button--raised mdl-js-ripple-effect   btneditar_combo editar_combopedido'><i class='material-icons'>edit</i> Editar Combo</button>"
        +"</div> ";
    
    return html;    
}



function gera_htmlPromocao_cg(item){
    var promocao_nome = item.nome;
    var promocao_preco= parseReal(item.preco);
    var combo_economia = parseReal(item.economia);
    var dadosmanip = JSON.stringify(item.dadosalter);
    var itens = item.itens;
    var cntitens = itens.length;
    
    var precomostrar = ": R$" + promocao_preco;
    var precoreal = parseFloat(item.preco);
    if(parseFloat(item.item_preco) > 0){
        precomostrar = " - Por apenas: R$ "+ promocao_preco;
    }else{
        precomostrar = " - Grátis";
    }
    
    var htmeconomia = "";
    if( parseFloat(item.economia)>0 ){
        htmeconomia = "<p class='economia'><i class='material-icons'>thumb_up</i> Você economizou R$ "+combo_economia+"</p>";
    }
    var html = "<div class='combo'  data-dadosalteracao='"+dadosmanip+"'>"
        +    "<p class='tit_combo_resumo'>"+promocao_nome+ precomostrar +"</p>"
        +    htmeconomia;

    for(var t=0; t<cntitens;t++){
        html+=   "<div class='item_resumo_combo'>"
            +        "<div class='det_item_resumo'>"
            +            "<p class='nomeitem_resumo'>"+itens[t].nome.linha1+"</p>"
            +            "<p class='descitem_resumo'>"+itens[t].nome.linha2+"</p>"
            +        "</div>"
            +        "<div class='clear'></div>"
            +    "</div>";
    }
    
    html+= "</div> ";    
    return html;    
}


function gera_htmlItemSimples(item){
    
    var preco = parseFloat(item.preco.venda);
    var precooriginal = parseFloat(item.preco.original);
    var desconto = parseFloat(item.preco.desconto);
    var qtd = parseInt(item.quantidade);
    var dadosmanip = JSON.stringify(item.dadosalter);
    var htmlpreco = "";
    
    preco = (preco*qtd);
    precooriginal = (precooriginal*qtd);
    desconto = (desconto*qtd);
    
    if(desconto > 0){
        htmlpreco = "<p class='preco_item_resumo_promo'><span class='promopreco'>de <s>"+parseReal(precooriginal)+"</s> por</span><br/>R$ "+parseReal(preco)+"</p>";
    }else{
        htmlpreco = "<p class='preco_item_resumo'>R$ "+parseReal(preco)+"</p>";
    }
    
    var html = "<div class='item_resumo'>"
        +    "<div class='dir_item_resumo'>"
        +        "<div class='qtd_item'  data-dadosalteracao='"+dadosmanip+"'>"
        +            "<a href='#' title='Remover' class='addmenos_item'>-</a>"
        +            "<input type='text' value='"+qtd+"' readonly='true'>"
        +            "<a href='#' title='Adicionar' class='addmais_item'>+</a>"
        +            "<div class='clear'></div>"
        +        "</div>"
        +        htmlpreco
        +    "</div>"
        +    "<div class='det_item_resumo'>"
        +        "<img src='"+item.urlfoto+"' width='44' class='icon_resumo'/>"
        +        "<p class='nomeitem_resumo' data-dadosalteracao='"+dadosmanip+"'>"+item.nome.linha1+" <i class='deletar_item material-icons'>delete</i></p>"
        +        "<p class='descitem_resumo'>"+item.nome.linha2+"</p>"
        +    "</div>"
        +    "<div class='clear'></div>"
        +"</div>";
    return html;
}

function gera_htmlItemComposto(item){
    var preco = parseFloat(item.preco.venda);
    var precooriginal = parseFloat(item.preco.original);
    var desconto = parseFloat(item.preco.desconto);
    var qtd = parseInt(item.quantidade);
    var dadosmanip = JSON.stringify(item.dadosalter);
    preco = (preco*qtd);
    precooriginal = (precooriginal*qtd);
    desconto = (desconto*qtd);
    
    var htmlpreco = "";
    if(desconto > 0){
        htmlpreco = "<p class='preco_item_resumo_promo'><span class='promopreco'>de <s>"+parseReal(precooriginal)+"</s> por</span><br/>R$ "+parseReal(preco)+"</p>";
    }else{
        htmlpreco = "<p class='preco_item_resumo'>R$ "+parseReal(preco)+"</p>";
    }
    
    var cntdetalhes = item.detalhes.length;
    
    var html = "<div class='item_resumo'>"
        +    "<div class='dir_item_resumo'>"
        +        "<div class='qtd_item' data-dadosalteracao='"+dadosmanip+"'>"
        +            "<a href='#' title='Remover' class='addmenos_item'>-</a>"
        +            "<input type='text' value='"+qtd+"' readonly='true'>"
        +            "<a href='#' title='Adicionar' class='addmais_item'>+</a>"
        +            "<div class='clear'></div>"
        +        "</div>"
        +        htmlpreco
        +    "</div>"
        +    "<div class='det_item_resumo'>"
        +        "<img src='"+item.urlfoto+"' width='44' class='icon_resumo'/>"
        +        "<p class='nomeitem_resumo' data-dadosalteracao='"+dadosmanip+"'>"+item.nome.linha1+" <i class='deletar_item material-icons'>delete</i></p>"
        +        "<p class='descitem_resumo'>"+item.nome.linha2+"</p>"
        +    "</div>";
    if(cntdetalhes > 0){
        html+=   "<div class='personalizacoes_item'><p>";
        for(var h=0; h<cntdetalhes; h++){
            html+=        "<strong>"+item.detalhes[h].linha1+": </strong> "+item.detalhes[h].linha2+"<br/>";
        }   
        html+=   "</p></div>";
    }
    if(item.permiteeditar === "S"){
        html+=   "<button class='mdl-button mdl-js-button btneditar_resumo editar_itempedido' data-dadosalteracao='"+dadosmanip+"'><i class='material-icons'>edit</i> Editar</button>";
    }
    html+=   "<div class='clear'></div>"
        +"</div>";
    return html;
}

/* new Resumo */

function gera_htmlItens_nw(item){
    var htmlitem = "";
    var tipoitem = item.item_tipo;
    var editar = item.item_permiteEditar;
    var premio = item.item_fidelidadePremio;

    if(tipoitem === "combo"){
        htmlitem += gera_htmlCombo_nw(item);
    }else if(tipoitem === "sozinho" && (editar === "N" || editar === null) && premio !== 'S'){
        htmlitem += gera_htmlItemSimples_nw(item, editar);
    }else if(tipoitem === "sozinho" && editar === "S" && premio !== 'S'){
        htmlitem += gera_htmlItemComposto_nw(item);
    }else if(tipoitem === "promocaoCompreGanhe"){
        htmlitem += gera_htmlPromocao_cg_nw(item);
    }else if(tipoitem === "sozinho" && (editar === "N" || editar === null) && premio === 'S'){
        htmlitem += gera_htmlPremioFidelidade(item);
    }else if(tipoitem === "sozinho" && editar === 'S' && premio === 'S'){
        htmlitem += gera_htmlPremioFidelidadeComposto(item);
    }
    
    return htmlitem;        
}

function gera_htmlCombo_nw(item){
    const qtd               = parseInt(item.qtd_combos) + 1;
    const combo_nome        = item.item_nome;
    const combo_preco       = item?.totalValue ? parseReal(parseFloat(item["totalValue"])) : parseReal(parseFloat(item.item_preco) * parseFloat(qtd));
    const combo_economia    = item?.totalDiscount ? parseReal(parseFloat(item["totalDiscount"])) : parseReal(parseFloat(item.item_precoValorDesconto) * parseFloat(qtd));
    const dadosmanip        = JSON.stringify(item.dadosalter);
    const itens             = item.item_itens;
    const cntitens          = itens.length;

    let htmeconomia = "";
    if( parseFloat(item.item_precoValorDesconto)>0 ){
        htmeconomia = "<p class='economia'><i class='material-icons'>thumb_up</i> Você economizou R$ "+combo_economia+"</p>";
    }

    var htmBotoesQtd = `<div class='btn_qtd_pedido' data-dadosalteracao='${dadosmanip}'>
      <span class='decreaseQuantityComboSummary qtd_menos_pedido'>-</span>
        <input type='text' class='qtd_txt_pedido inteiro inputQuantityComboSummary' type='number' max-length='3' value='${qtd}' data-quantity-current='${qtd}' data-id='${item.item_codigoItensCombo}'>
      <span class='incrementQuantityComboSummary qtd_mais_pedido'>+</span>
    </div>`

    const pontos = item.item_fidelidadePontos;
    if(item.item_fidelidadePremio == 'S'){
        htmeconomia = "<p class='economia' style='text-align:center; margin-bottom:10px;'>🎁 Você usou "+pontos+" pontos</p>";
        htmBotoesQtd = '';
    }

    let html = `<div class='item_resumo'>
                    <div class='dir_item_resumo'>
                        <div class='qtd_item'  data-dadosalteracao='${dadosmanip}'>
                        ${htmBotoesQtd}
                        </div>
                    </div>
                    <p class='tit_combo_resumo'>${combo_nome}: R$ ${combo_preco}</p>
                    <div class='clear'></div>
                    ${htmeconomia}
                `;


    for (let t = 0; t < cntitens; t += 1) {
        
        const oitem     = itens[t];
        const tamanho   = (oitem.item_composto.length > 0) ? `${oitem.item_nomeTamanho}: ` : `${oitem.item_nomeCategoria}: `;
        
        const linha1_t = `${oitem.item_quantidade} - ${tamanho}${oitem.item_nome}`;
        const linha2_t = '';
        
        html += `<div class='item_resumo_combo'>
                    <div class='desc_item_resumo'>
                        <p class='nomeitem_resumo'>${linha1_t}</p>
                        <p class='descitem_resumo'>${linha2_t}</p>
                    </div>
                    <div class='clear'></div>
                `;

        html += geraHtmlComboDetalhado(oitem);
    }
    
    html+=   "<button class='mdl-button mdl-js-button btn_excluircombo deletarcombo_item'><i class='material-icons'>delete</i> Remover</button>"
        +    "<button class='mdl-button mdl-js-button btneditar_combo editar_combopedido'><i class='material-icons'>edit</i> Editar Combo</button>"
        +"</div>";
    return html;    
    
}

function gera_htmlPremioFidelidade(item){
    
    var pontos = item.item_fidelidadePontos;
    var htmeconomia = "<p class='economia' style='text-align:center; margin-bottom:10px;'>🎁 Você usou "+pontos+" pontos</p>";
    var qtd = parseInt(item.item_quantidade);
    const typeUnit = item?.item_typeUnit ?? 'UN';
    let strQuantity = typeUnit == 'KG' ? `${(qtd / 1000).toFixed(3).replace('.', ',')} KG` : qtd;
    
    var l_icone = item.item_icone;
    var l_nome = item.item_nome;
    var l_categ = item.item_nomeCategoria;
    if(item.item_permiteEditar === "N"){
        l_icone = item.item_composto[0].item_icone;
        l_nome = item.item_composto[0].item_nome;
        l_categ = item.item_composto[0].item_nomeCategoria;
    }

    var id_itenspedido = item.item_codigoItens;
    
    var html = "<div class='item_resumo'>"
        + htmeconomia
        +    "<div class='det_item_resumo'>"
        +        "<img src='"+l_icone+"' width='44' class='icon_resumo'/>"
        +        "<p class='nomeitem_resumo'>"+strQuantity+ " " + l_nome+" <a class='deletar_premio' href='#' data-key='"+id_itenspedido+"'><i class='material-icons'>delete</i></a></p>"
        +        "<p class='descitem_resumo'>Prêmio Programa de Fidelidade</p>"
        +    "</div>"
        +    "<div class='clear'></div>"
        +"</div>";
    return html;   
}

function gera_htmlPremioFidelidadeComposto(item){
    
    var qtd = parseInt(item.item_quantidade);

    var pontos = item.item_fidelidadePontos;
    var htmeconomia = "<p class='economia' style='text-align:center; margin-bottom:10px;'>🎁 Você usou "+pontos+" pontos</p>";
    
    var htmdetalhes = "";
    var cnt_sabores = item.item_composto.length;
    
    var l_icone = item.item_icone;
    var l_nome = item.item_nome;
    var l_tamanho = item.item_nomeTamanho;

    var id_itenspedido = item.item_codigoItens;
    
    if(cnt_sabores === 1){
        l_icone = item.item_composto[0].item_icone;
    }
    
    for(var i=0; i<cnt_sabores; i++){
        var cnt_indadd = item.item_composto[i].item_ingredientesAdicionais.length;
        var cnt_ingrem = item.item_composto[i].item_ingredientesRemovidos.length;
        item.item_composto[i].item_nome;
        var listings = "";
        for(var ig=0; ig<cnt_ingrem; ig++){
            var nomeing = item.item_composto[i].item_ingredientesRemovidos[ig].item_nome;
            listings += "s/ "+nomeing+"; ";
        }
        
        for(var ig=0; ig<cnt_indadd; ig++){
            var nomeing = item.item_composto[i].item_ingredientesAdicionais[ig].item_nome;
            listings += "c/ "+nomeing+";";
        }
        
        if(cnt_indadd>0 || cnt_ingrem>0){
            htmdetalhes += "<strong>"+item.item_composto[i].item_nome+": </strong> "+listings+"<br/>";
        }
        
    }
    
    var cnt_opcobg = item.item_opcionalObrigatorio.length;
    var cnt_opcadd = item.item_opcionaisAdicionaveis.length;
    var cnt_obs = item.item_observacoes.length;
    let cnt_compositions = item.item_compositions ? item.item_compositions.length : 0;

    if(cnt_opcobg!=0){
        var nometipo = "Massa";
        var nomeitemm = "";
        var nometipo_arr = item.item_opcionalObrigatorio.item_nome.split(":");
        nomeitemm = item.item_opcionalObrigatorio.item_nome;
        if(nometipo_arr.length==2){
            nometipo = nometipo_arr[0];
            nomeitemm = nometipo_arr[1];
        }
        htmdetalhes += "<strong>"+nometipo+": </strong> "+nomeitemm+"<br/>";
    }
    
    if(cnt_opcadd>0){
        var listabd = "";
        for(var hsd=0; hsd<cnt_opcadd; hsd++){
        
            var nometipo = "Borda";
            var nomeitemm = "";
            var nometipo_arr = item.item_opcionaisAdicionaveis[hsd].item_nome.split(":");
            nomeitemm = item.item_opcionaisAdicionaveis[hsd].item_nome;
            if(nometipo_arr.length==2){
                nometipo = nometipo_arr[0];
                listabd += nometipo_arr[1]+"; ";
            }
            
        }
        htmdetalhes += "<strong>"+nometipo+": </strong> "+listabd+"<br/>";
    }

    if (cnt_compositions > 0) {
      let categories = new Set();
      for (let i = 0; i < cnt_compositions; i++) {
        categories.add(item.item_compositions[i].categoryId);
      }

      categories = Array.from(categories);
      for (let i = 0; i < categories.length; i++) {
        let compositions = item.item_compositions.filter(element => element['categoryId'] == categories[i]);

        let categoryName = compositions[0]['categoryName'];
        let listCompositions = "";
        for (let x = 0; x < compositions.length; x++) {
          listCompositions += ` ${compositions[x]['amount']}x ${compositions[x]['compositionName']};`;
        }

        htmdetalhes += `<strong>${categoryName}: </strong>${listCompositions}<br/>`;

        let compositionsAdd = item.item_compositionsAdd.filter(element => element['categoryId'] == categories[i]);
        if (compositionsAdd.length > 0) {
          let categoryNameAdd = compositionsAdd[0]['categoryName'];
          let listCompositionsAdd = "";
          for (let x = 0; x < compositionsAdd.length; x++) {
            listCompositionsAdd += ` ${compositionsAdd[x]['amount']}x ${compositionsAdd[x]['compositionName']};`;
          }
  
          htmdetalhes += `<strong>Adicional ${categoryNameAdd}: </strong>${listCompositionsAdd}<br/>`;
        }
      }
    }

    if(cnt_obs>0){
        var listaobs = "";
        for(var hsd=0; hsd<cnt_obs; hsd++){        
            listaobs += item.item_observacoes[hsd].item_nome + "; ";            
        }
        htmdetalhes += "<strong>Observações: </strong> "+listaobs+"<br/>";
    }
    
    var html = "<div class='item_resumo'>"
        + htmeconomia
        +    "<div class='det_item_resumo reward-description-summary'>"
        +        "<div class='item-description'>"

        +           "<img src='"+l_icone+"' width='44' class='icon_resumo'/>"
        +           "<p class='nomeitem_resumo'>"+qtd+ " " +l_tamanho+" <a class='deletar_premio' href='#' data-key='"+id_itenspedido+"'><i class='material-icons'>delete</i></a></p>"
        +           "<p class='descitem_resumo'>"+l_nome+"</p>"
        +        "</div>";

    if (item.item_preco > 0) {
      html += `
        <div class='item-price'>
          <p class='preco_item_resumo'>R$ ${parseReal(item.item_preco)}</p>
        </div>
      `;
    }

    html += "</div>"

    if(htmdetalhes != ""){
        html+=   "<div class='personalizacoes_item'><p>";
        html+=   htmdetalhes; 
        html+=   "</p></div>";
    }
    html+=  "<div class='clear'></div>";
    html+=  "</div>";
    return html;
}



function gera_htmlPromocao_cg_nw(item){
    
    var promocao_nome = item.item_nome;
    var promocao_preco= parseReal(item.item_preco);
    var combo_economia = parseReal(item.item_precoValorDesconto);
    var dadosmanip = JSON.stringify(item.dadosalter);
    var itens = item.item_itens;
    var cntitens = itens.length;
    
    var precomostrar = ": R$" + promocao_preco;
    var precoreal = parseFloat(item.item_precoOriginal);
    if(parseFloat(item.item_preco) > 0){
        precomostrar = " - Por apenas: R$ "+ promocao_preco;
    }else{
        precomostrar = " - Grátis";
    }
    
    var htmeconomia = "";
    if( parseFloat(item.item_precoValorDesconto)>0 ){
        htmeconomia = "<p class='economia'><i class='material-icons'>thumb_up</i> Você economizou R$ "+combo_economia+"</p>";
    }
    var html = "<div class='combo'  data-dadosalteracao='"+dadosmanip+"'>"
        +    "<p class='tit_combo_resumo'>"+promocao_nome+ precomostrar +"</p>"
        +    htmeconomia;

    for(var t=0; t<cntitens;t++){
        var opsobs = "";
        var oitem = itens[t];
        var tamanho = (oitem.item_composto.length>0)? oitem.item_nomeTamanho + ": " : oitem.item_nomeCategoria+": ";
        
        var cntobg = oitem.item_opcionalObrigatorio.length;
        var cntadd = oitem.item_opcionaisAdicionaveis.length;
        
        if(cntobg!=0){            
            opsobs += " + "+ oitem.item_opcionalObrigatorio.item_nome;
        }
        if(cntadd>0){
            var listabd = "";
            for(var hsd=0; hsd<cntadd; hsd++){
                var nometipo = "Borda";
                var nomeitemm = "";
                var nometipo_arr = oitem.item_opcionaisAdicionaveis[hsd].item_nome.split(":");
                nomeitemm = oitem.item_opcionaisAdicionaveis[hsd].item_nome;
                if(nometipo_arr.length==2){
                    nometipo = nometipo_arr[0];
                    listabd += nometipo_arr[1]+"; ";
                }
            }
            opsobs += " + " + nometipo+": "+listabd;
        }
        
        var linha1_t = oitem.item_quantidade + " - " + tamanho + oitem.item_nome + opsobs;
        var linha2_t = "";
        
        html+=   "<div class='item_resumo_combo'>"
            +        "<div class='det_item_resumo'>"
            +            "<p class='nomeitem_resumo'>"+linha1_t+"</p>"
            +            "<p class='descitem_resumo'>"+linha2_t+"</p>"
            +        "</div>"
            +        "<div class='clear'></div>"
            +    "</div>";
    }
    
    html+= "</div> ";    
    return html;    
}


function gera_htmlItemSimples_nw(item, editar){
    
    var preco = parseFloat(item.item_preco);
    var precooriginal = parseFloat(item.item_precoOriginal);
    var desconto = parseFloat(item.item_precoValorDesconto);
    var qtd = parseInt(item.item_quantidade);
    var dadosmanip = JSON.stringify(item.dadosalter);
    var htmlpreco = "";
    const typeUnit = item?.item_typeUnit ?? 'UN';
    
    preco = (preco*qtd);
    precooriginal = (precooriginal*qtd);
    desconto = (desconto*qtd);
    
    if(desconto > 0){
        htmlpreco = "<p class='preco_item_resumo_promo'><span class='promopreco'>de <s>"+parseReal(precooriginal)+"</s> por</span><br/>R$ "+parseReal(preco)+"</p>";
    }else{
        htmlpreco = "<p class='preco_item_resumo'>R$ "+parseReal(preco)+"</p>";
    }
    
    
    var l_icone = item.item_icone;
    var l_nome = item.item_nome;
    var l_categ = item.item_nomeCategoria;
    if(editar === "N"){
        l_icone = item.item_composto[0].item_icone;
        l_nome = item.item_composto[0].item_nome;
        l_categ = item.item_composto[0].item_nomeCategoria;
    }
    
    let html = "";
    if (typeUnit == 'UN') {
      html = "<div class='item_resumo'>"
          +    "<div class='dir_item_resumo'>"
          +         "<div class='btn_qtd_pedido qtd_item' data-dadosalteracao='" + dadosmanip + "'>"
          +           "<span class='decreaseQuantityProductSummary qtd_menos_pedido'>-</span>"
          +           `<input type='text' class='qtd_txt_pedido inteiro inputQuantityProductSummary' type='number' max-length='3' value='${qtd}' data-quantity-current='${qtd}' data-id='${item.item_codigoItens}'>`
          +           "<span class='incrementQuantityProductSummary qtd_mais_pedido'>+</span>"
          +         "</div>"
          +        htmlpreco
          +    "</div>"
          +    "<div class='det_item_resumo'>"
          +        "<img src='"+l_icone+"' width='44' class='icon_resumo'/>"
          +        "<p class='nomeitem_resumo' data-dadosalteracao='"+dadosmanip+"'>"+l_nome+" <i class='deletar_item material-icons'>delete</i></p>"
          +        "<p class='descitem_resumo'>"+l_categ+"</p>"
          +    "</div>"
          +    "<div class='clear'></div>"
          +"</div>";
    } else {
      const quantity = (parseInt(item['item_quantidade']) / 1000).toFixed(3).replace('.', ',');
      html = `
        <div class='item_resumo'>
          <div class='dir_item_resumo'>
            <p class="quantityItemKg">${quantity} KG</p>
            ${htmlpreco}
          </div>
          <div class='det_item_resumo'>
            <img src='${l_icone}' width='44' class='icon_resumo'/>
            <p class='nomeitem_resumo' data-dadosalteracao='${dadosmanip}'>${l_nome} 
              <i class='deletar_item material-icons'>delete</i>
            </p>
            <p class='descitem_resumo'>${l_categ}</p>
            <div class="div_resumo_edit_item_kg">
              <button class='mdl-button mdl-js-button btneditar_resumo edit_item_kg'  data-data='${dadosmanip}' data-name='${item['item_nome']}' data-quantitySale='${item['item_quantitySale']}' data-price='${item['item_preco']}' data-quantity='${item['item_quantidade']}' data-description="${item["item_descricao"]}" data-imageurl="${l_icone}"><i class='material-icons'>edit</i> Editar</button>
            </div>
          </div>
          <div class='clear'></div>
        </div>`
      ;
    }
    return html;
}

function gera_htmlItemComposto_nw(item){
    var preco = parseFloat(item.item_preco);
    var precooriginal = item?.item_precoOriginalComAdd ? parseFloat(item.item_precoOriginalComAdd) : parseFloat(item.item_precoOriginal);
    var desconto = item?.item_precoOriginalComAdd ? parseFloat(precooriginal - preco) : parseFloat(item.item_precoValorDesconto);
    var qtd = parseInt(item.item_quantidade);
    var dadosmanip = JSON.stringify(item.dadosalter);
    var htmlpreco = "";

    let obs_texto = item["item_obs_manual"] ? item["item_obs_manual"] : false;
    
    preco = (preco*qtd);
    precooriginal = (precooriginal*qtd);
    desconto = (desconto*qtd);
    
    if(desconto > 0){
        htmlpreco = "<p class='preco_item_resumo_promo'><span class='promopreco'>de <s>"+parseReal(precooriginal)+"</s> por</span><br/>R$ "+parseReal(preco)+"</p>";
    }else{
        htmlpreco = "<p class='preco_item_resumo'>R$ "+parseReal(preco)+"</p>";
    }
    
    var htmdetalhes = "";
    var cnt_sabores = item.item_composto.length;
    
    var l_icone = item.item_icone;
    var l_nome = item.item_nome;
    var l_tamanho = item.item_nomeTamanho;
    
    if(cnt_sabores === 1){
        l_icone = item.item_composto[0].item_icone;
    }
    
    for(var i=0; i<cnt_sabores; i++){
        var cnt_indadd = item.item_composto[i].item_ingredientesAdicionais.length;
        var cnt_ingrem = item.item_composto[i].item_ingredientesRemovidos.length;
        item.item_composto[i].item_nome;
        var listings = "";
        for(var ig=0; ig<cnt_ingrem; ig++){
            var nomeing = item.item_composto[i].item_ingredientesRemovidos[ig].item_nome;
            listings += "s/ "+nomeing+"; ";
        }
        
        for(var ig=0; ig<cnt_indadd; ig++){
            let ing = item.item_composto[i].item_ingredientesAdicionais[ig];
            let nome_ing = ing.item_nome;
            let qtd_ing = ing.item_quantidade;
            if(qtd_ing && qtd_ing > 1) {
              listings += `c/ ${qtd_ing}x ${nome_ing}; `;
            } else {
              listings += "c/ "+nome_ing+"; ";
            }
        }
        
        if(cnt_indadd>0 || cnt_ingrem>0){
            htmdetalhes += "<strong>"+item.item_composto[i].item_nome+": </strong> "+listings+"<br/>";
        }
        
    }
    
    var cnt_opcobg = item.item_opcionalObrigatorio.length;
    var cnt_opcadd = item.item_opcionaisAdicionaveis.length;
    var cnt_obs = item.item_observacoes.length;
    let cnt_compositions = item.item_compositions ? item.item_compositions.length : 0;
    
    if(cnt_opcobg!=0){
        var nometipo = "Massa";
        var nomeitemm = "";
        var nometipo_arr = item.item_opcionalObrigatorio.item_nome.split(":");
        nomeitemm = item.item_opcionalObrigatorio.item_nome;
        if(nometipo_arr.length==2){
            nometipo = nometipo_arr[0];
            nomeitemm = nometipo_arr[1];
        }
        htmdetalhes += "<strong>"+nometipo+": </strong> "+nomeitemm+"<br/>";
    }
    
    if(cnt_opcadd>0){
        var listabd = "";
        for(var hsd=0; hsd<cnt_opcadd; hsd++){
        
            var nometipo = "Borda";
            var nomeitemm = "";
            var nometipo_arr = item.item_opcionaisAdicionaveis[hsd].item_nome.split(":");
            nomeitemm = item.item_opcionaisAdicionaveis[hsd].item_nome;
            if(nometipo_arr.length==2){
                nometipo = nometipo_arr[0];
                listabd += nometipo_arr[1]+"; ";
            }
            
        }
        htmdetalhes += "<strong>"+nometipo+": </strong> "+listabd+"<br/>";
    }

    if (cnt_compositions > 0) {
      let categories = new Set();
      for (let i = 0; i < cnt_compositions; i++) {
        categories.add(item.item_compositions[i].categoryId);
      }

      categories = Array.from(categories);
      for (let i = 0; i < categories.length; i++) {
        let compositions = item.item_compositions.filter(element => element['categoryId'] == categories[i]);

        let categoryName = compositions[0]['categoryName'];
        let listCompositions = "";
        for (let x = 0; x < compositions.length; x++) {
          listCompositions += ` ${compositions[x]['amount']}x ${compositions[x]['compositionName']};`;
        }

        htmdetalhes += `<strong>${categoryName}: </strong>${listCompositions}<br/>`;

        let compositionsAdd = item.item_compositionsAdd.filter(element => element['categoryId'] == categories[i]);
        if (compositionsAdd.length > 0) {
          let categoryNameAdd = compositionsAdd[0]['categoryName'];
          let listCompositionsAdd = "";
          for (let x = 0; x < compositionsAdd.length; x++) {
            listCompositionsAdd += ` ${compositionsAdd[x]['amount']}x ${compositionsAdd[x]['compositionName']};`;
          }
  
          htmdetalhes += `<strong>Adicional ${categoryNameAdd}: </strong>${listCompositionsAdd}<br/>`;
        }
      }
    }

    if(cnt_obs>0){
        var listaobs = "";
        for(var hsd=0; hsd<cnt_obs; hsd++){        
            listaobs += item.item_observacoes[hsd].item_nome + "; ";            
        }
        htmdetalhes += "<strong>Observações: </strong> "+listaobs+"<br/>";
    }

    if(obs_texto){
      htmdetalhes += "<strong>Obs. Cliente: </strong> "+obs_texto+"<br/>";
    }

    var html = "<div class='item_resumo'>"
        +    "<div class='dir_item_resumo'>"
        +         "<div class='btn_qtd_pedido qtd_item' data-dadosalteracao='" + dadosmanip + "'>"
        +           "<span class='decreaseQuantityProductSummary qtd_menos_pedido'>-</span>"
        +           `<input type='text' class='qtd_txt_pedido inteiro inputQuantityProductSummary' type='number' max-length='3' value='${qtd}' data-quantity-current='${qtd}' data-id='${item.item_codigoItens}'>`
        +           "<span class='incrementQuantityProductSummary qtd_mais_pedido'>+</span>"
        +         "</div>"
        +        htmlpreco
        +    "</div>"
        +    "<div class='det_item_resumo'>"
        +        "<img src='"+l_icone+"' width='44' class='icon_resumo'/>"
        +        "<p class='nomeitem_resumo' data-dadosalteracao='"+dadosmanip+"'>"+l_tamanho+" <i class='deletar_item material-icons'>delete</i></p>"
        +        "<p class='descitem_resumo'>"+l_nome+"</p>"
        +    "</div>";
    if(htmdetalhes != ""){
        html+=   "<div class='personalizacoes_item'><p>";
        html+=   htmdetalhes; 
        html+=   "</p></div>";
    }
    if(item.item_permiteEditar === "S"){
        html+=   "<button class='mdl-button mdl-js-button btneditar_resumo editar_itempedido'  data-dadosalteracao='"+dadosmanip+"'><i class='material-icons'>edit</i> Editar</button>";
    }
    html+=   "<div class='clear'></div>"
        +"</div>";
    return html;
}

function geraHtmlComboDetalhado(item) {
    const tipoitem  = item.item_tipo;
    const editar    = item.item_permiteEditar;
    const premio    = item.item_fidelidadePremio;

    if (tipoitem === 'sozinho' && editar === 'S' && premio !== 'S') {
        return geraDetalhamentoItemComposto(item);
    }
    return '</div>';
}

function geraDetalhamentoItemComposto(item) {
    const desconto      = parseFloat(item.item_precoValorDesconto);
    const qtd           = parseInt(item.item_quantidade);
    const dadosmanip    = JSON.stringify(item.dadosalter);
    let preco           = parseFloat(item.item_preco);
    let precooriginal   = parseFloat(item.item_precoOriginal);
    let htmlpreco       = '';
    
    preco               = (preco * qtd);
    precooriginal       = (precooriginal * qtd);
    
    htmlpreco = "<p class='preco_item_resumo'>R$ "+parseReal(preco)+"</p>";
    if (desconto > 0) {
        htmlpreco = "<p class='preco_item_resumo_promo'><span class='promopreco'>de <s>"+parseReal(precooriginal)+"</s> por</span><br/>R$ "+parseReal(preco)+"</p>";
    }
    
    let htmdetalhes     = '';
    const cnt_sabores   = item.item_composto.length;
    
    let l_icone         = item.item_icone;
    
    if(cnt_sabores === 1) {
        l_icone = item.item_composto[0].item_icone;
    }
    
    for (let i = 0; i < cnt_sabores; i += 1) {
        const cnt_indadd    = item.item_composto[i].item_ingredientesAdicionais.length;
        const cnt_ingrem    = item.item_composto[i].item_ingredientesRemovidos.length;
        item.item_composto[i].item_nome;
        let listings        = '';
        for (let ig = 0; ig < cnt_ingrem; ig += 1) {
            const nomeing   = item.item_composto[i].item_ingredientesRemovidos[ig].item_nome;
            listings        += `s/ ${nomeing}; `;
        }
        
        for (let ig = 0; ig < cnt_indadd; ig += 1) {
          let ing = item.item_composto[i].item_ingredientesAdicionais[ig];
          let nome_ing = ing.item_nome;
          let qtd_ing = ing.item_quantidade;
          if(qtd_ing && qtd_ing > 1) {
            listings += `c/ ${qtd_ing}x ${nome_ing};`;
          } else {
            listings += "c/ "+nome_ing+";";
          }
        }
        
        if (cnt_indadd > 0 || cnt_ingrem > 0) {
            htmdetalhes += `<strong>${item.item_composto[i].item_nome}: </strong> ${listings}<br/>`;
        }
        
    }
    
    const cnt_opcobg  = item.item_opcionalObrigatorio.length;
    const cnt_opcadd  = item.item_opcionaisAdicionaveis.length;
    const cnt_obs     = item.item_observacoes.length;
    let cnt_compositions = item.item_compositions ? item.item_compositions.length : 0;
    const extraInfo = item.item_obs_manual ?? null;
    
    if (cnt_opcobg != 0) {
        const nometipo_arr  = item.item_opcionalObrigatorio.item_nome.split(":");
        let nometipo        = 'Massa';
        let nomeitemm       = '';
        nomeitemm           = item.item_opcionalObrigatorio.item_nome;
        if (nometipo_arr.length == 2) {
            nometipo    = nometipo_arr[0];
            nomeitemm   = nometipo_arr[1];
        }
        htmdetalhes += `<strong>${nometipo}: </strong> ${nomeitemm}<br/>`;
    }
    
    if (cnt_opcadd > 0) {
        let listabd         = '';
        let nometipo        = 'Borda';
        let nomeitemm       = '';
        let nometipo_arr    = '';
        for (let hsd = 0; hsd < cnt_opcadd; hsd += 1) {
            nomeitemm       = item.item_opcionaisAdicionaveis[hsd].item_nome;
            nometipo_arr    = item.item_opcionaisAdicionaveis[hsd].item_nome.split(":");
            if (nometipo_arr.length == 2) {
                nometipo = nometipo_arr[0];
                listabd += `${nometipo_arr[1]}; `;
            }
            
        }
        htmdetalhes += `<strong>${nometipo}: </strong> ${listabd}<br/>`;
    }

    if (cnt_compositions > 0) {
      let categories = new Set();
      for (let i = 0; i < cnt_compositions; i++) {
        categories.add(item.item_compositions[i].categoryId);
      }

      categories = Array.from(categories);
      for (let i = 0; i < categories.length; i++) {
        let compositions = item.item_compositions.filter(element => element['categoryId'] == categories[i]);

        let categoryName = compositions[0]['categoryName'];
        let listCompositions = "";
        for (let x = 0; x < compositions.length; x++) {
          listCompositions += ` ${compositions[x]['amount']}x ${compositions[x]['compositionName']};`;
        }

        htmdetalhes += `<strong>${categoryName}: </strong>${listCompositions}<br/>`;

        let compositionsAdd = item.item_compositionsAdd.filter(element => element['categoryId'] == categories[i]);
        if (compositionsAdd.length > 0) {
          let categoryNameAdd = compositionsAdd[0]['categoryName'];
          let listCompositionsAdd = "";
          for (let x = 0; x < compositionsAdd.length; x++) {
            listCompositionsAdd += ` ${compositionsAdd[x]['amount']}x ${compositionsAdd[x]['compositionName']};`;
          }
  
          htmdetalhes += `<strong>Adicional ${categoryNameAdd}: </strong>${listCompositionsAdd}<br/>`;
        }
      }
    }
    
    if (cnt_obs > 0) {
        let listaobs = '';
        for (let hsd = 0; hsd < cnt_obs; hsd += 1) {        
            listaobs += `${item.item_observacoes[hsd].item_nome}; `;            
        }
        htmdetalhes += `<strong>Observações: </strong> ${listaobs}<br/>`;
    }

    if (extraInfo) {
      htmdetalhes += `<strong>Obs. Cliente: </strong> ${extraInfo}<br/>`;
    }

    let html = `<div class="combo-detalhamento_item">`;
    if (htmdetalhes != '') {
        html += '<div class="combo-personalizacoes_item"><p>';
        html += htmdetalhes; 
        html += '</p></div>';            
    }
    html += "</div>";
    html += '<div class="clear"></div></div>';

    return html;
}


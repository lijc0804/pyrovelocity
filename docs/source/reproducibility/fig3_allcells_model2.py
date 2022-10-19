import scvelo as scv
import os
from scvelo.datasets import simulation
import numpy as np
import matplotlib.pyplot as plt
from dynamical_velocity2 import PyroVelocity
from dynamical_velocity2.data import load_data
from scipy.stats import pearsonr, spearmanr
import seaborn as sns
from dynamical_velocity2.data import load_data
import cospar as cs
import numpy as np
import scvelo as scv
cs.logging.print_version()
cs.settings.verbosity=2
cs.settings.data_path='LARRY_data' # A relative path to save data. If not existed before, create a new one.
cs.settings.figure_path='LARRY_figure' # A relative path to save figures. If not existed before, create a new one.
cs.settings.set_figure_params(format='png',figsize=[4,3.5],dpi=75,fontsize=14,pointsize=2)
import scvelo as scv
from scvelo.datasets import simulation
import numpy as np
import matplotlib.pyplot as plt
from dynamical_velocity2 import PyroVelocity
from dynamical_velocity2.data import load_data
from scipy.stats import pearsonr, spearmanr
import seaborn as sns
from dynamical_velocity2.data import load_data
from dynamical_velocity2.api import train_model
import seaborn as sns
import pandas as pd
from dynamical_velocity2.plot import plot_posterior_time, plot_gene_ranking,\
      vector_field_uncertainty, plot_vector_field_uncertain,\
      plot_mean_vector_field, project_grid_points,rainbowplot,denoised_umap,\
      us_rainbowplot, plot_arrow_examples

adata_input = scv.read("larry_invitro_adata_with_scvelo_dynamicalvelocity.h5ad")
adata = scv.read("larry_invitro_adata_sub_raw.h5ad")

adata_cospar = scv.read("LARRY_MultiTimeClone_Later_FullSpace0_t*2.0*4.0*6_adata_with_transition_map.h5ad")
adata_cytotrace = scv.read("larry_invitro_adata_sub_raw_withcytotrace.h5ad")
adata_vel = scv.read("larry_invitro_adata_with_scvelo_dynamicalvelocity.h5ad")

cs.pl.fate_potency(adata_cospar, used_Tmap='transition_map',
                   map_backward=True,method='norm-sum',color_bar=True,fate_count=True)

adata_input.layers['raw_spliced']   = adata[:, adata_input.var_names].layers['spliced']
adata_input.layers['raw_unspliced'] = adata[:, adata_input.var_names].layers['unspliced']

adata_input.obs['u_lib_size_raw'] = adata_input.layers['unspliced'].toarray().sum(-1)
adata_input.obs['s_lib_size_raw'] = adata_input.layers['spliced'].toarray().sum(-1)

# adata_input.obs['u_lib_size_raw'] = adata.layers['unspliced'].toarray().sum(-1)
# adata_input.obs['s_lib_size_raw'] = adata.layers['spliced'].toarray().sum(-1)


adata_model_pos_split = train_model(adata_input,
                                    max_epochs=1000, svi_train=True, log_every=100,
                                    patient_init=45,
                                    batch_size=4000, use_gpu=1, cell_state='state_info',
                                    include_prior=True,
                                    offset=True,
                                    library_size=True,
                                    patient_improve=1e-3,
                                    model_type='auto',
                                    guide_type='auto',
                                    #kinetics_num=3,
                                    train_size=1.0)

pos = adata_model_pos_split[1]
scale = 1
#pos_ut = pos['ut'].mean(axis=0)
#pos_st = pos['st'].mean(axis=0)
#pos_u = pos['u'].mean(axis=0)
#pos_s = pos['s'].mean(axis=0)
#pos_v = pos['beta'].mean(0)[0]* pos_ut / scale - pos['gamma'].mean(0)[0] * pos_st
#velocity_samples = pos['beta'] * pos['ut'] / scale - pos['gamma'] * pos['st']
pos_time = pos['cell_time'].mean(0)


def check_shared_time(adata_model_pos, adata):
    gold_standard = adata_cospar.obs['fate_potency'].values
    select, = np.where(~np.isnan(gold_standard))
    print(pos_time.shape)
    print(spearmanr(pos_time.squeeze()[select], gold_standard[select]))

    adata.obs['cell_time'] = adata_model_pos[1]['cell_time'].squeeze().mean(0)
    #adata.obs['lineage'] = adata_model_pos[1]['kinetics_lineage'].squeeze().mean(0)
    #adata.obs['lineage_prob'] = adata_model_pos[1]['kinetics_prob'].mean(0).argmax(-1).squeeze()
    adata.obs['1-Cytotrace'] = 1-adata_cytotrace.obs['cytotrace']
    fig, ax = plt.subplots(1, 6)
    fig.set_size_inches(23, 3)
    scv.tl.latent_time(adata_vel)
    scv.pl.scatter(adata_vel, color='latent_time', show=False,
                   ax=ax[0], title='scvelo %.2f' % spearmanr(1-adata_cytotrace.obs.cytotrace, adata.obs.latent_time)[0],
                   cmap='RdBu_r', basis='emb')
    scv.pl.scatter(adata, color='cell_time', show=False, basis='emb',
                   ax=ax[1], title='pyro %.2f' % spearmanr(1-adata_cytotrace.obs.cytotrace, adata.obs.cell_time)[0])
    scv.pl.scatter(adata, color='1-Cytotrace', show=False, ax=ax[2], basis='emb')
    scv.pl.scatter(adata_cospar, color='fate_potency', show=False, ax=ax[3], basis='emb')
    #scv.pl.scatter(adata, color='lineage', show=False, ax=ax[4], basis='emb')
    #scv.pl.scatter(adata, color='lineage_prob', show=False, ax=ax[5], basis='emb')
    print(spearmanr(adata.obs.cell_time, adata_vel.obs.latent_time))
    fig.savefig("fig3_all_test_sub_model2.pdf", facecolor=fig.get_facecolor(),
                bbox_inches='tight', edgecolor='none', dpi=300)

check_shared_time(adata_model_pos_split, adata_input)

fig, ax = plt.subplots()
volcano_data, _ = plot_gene_ranking([adata_model_pos_split[1]], [adata_input], ax=ax, time_correlation_with='st')
fig.savefig("fig3_all_test_volcano_sub_model2.pdf", facecolor=fig.get_facecolor(), bbox_inches='tight', edgecolor='none', dpi=300)
fig = us_rainbowplot(volcano_data.sort_values("mean_mae", ascending=False).head(50).sort_values("time_correlation", ascending=False).head(3).index,
                     adata_input, adata_model_pos_split[1], data=['st', 'ut'],
                     cell_state='state_info')
#fig = us_rainbowplot(['Grin2b', 'Map1b', 'Ppp3ca'],
fig.savefig("fig3_all_test_rainbow_sub_model2.pdf", facecolor=fig.get_facecolor(),
            bbox_inches='tight', edgecolor='none', dpi=300)

v_map_all, embeds_radian, fdri = vector_field_uncertainty(adata_input, adata_model_pos_split[1], basis='emb', denoised=False, n_jobs=5)

fig, ax = plt.subplots()
embed_mean = plot_mean_vector_field(adata_model_pos_split[1], adata_input,
                                    ax=ax, basis='emb', n_jobs=10)
fig.savefig("fig3_test_vecfield_sub_model2.pdf", facecolor=fig.get_facecolor(),
            bbox_inches='tight', edgecolor='none', dpi=300)

#adata_input.write("fig3_larry_allcells_top2000_model2.h5ad")
#adata_model_pos_split[0].save('Fig3_allcells_model2', overwrite=True)
#
#result_dict = {"adata_model_pos": adata_model_pos_split[1], "v_map_all": v_map_all, "embeds_radian": embeds_radian, "fdri": fdri, "embed_mean": embed_mean}
#import pickle
#
#with open("fig3_allcells_data_model2.pkl", "wb") as f:
#    pickle.dump(result_dict, f)    

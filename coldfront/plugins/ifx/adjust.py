# -*- coding: utf-8 -*-

'''
Code for ad hoc billing adjustments

Created on  2023-04-10

@author: Aaron Kitzmiller <akitzmiller@g.harvard.edu>
@copyright: 2023 The Presidents and Fellows of Harvard College.
All rights reserved.
@license: GPL v2.0
'''

import logging

from ifxbilling.models import Account, BillingRecord
from coldfront.plugins.ifx.models import ProjectOrganization

logger = logging.getLogger(__name__)

PROJECTS = {
    'holy-isilon/tier1': [
        'acc_lab',
        'hoekstra_lab',
        'grad_lab',
        'eddy_lab',
        'gaab_mri_l3',
        'ham_lab',
        'pooling_l3',
        'dulac_lab',
        'park_lab',
        'tingley_harvardx_l3',
        'lemos_lab',
        'iqss_staff_l3',
        'murphy_secure',
        'hekstra_lab',
        'pallais_ae17_eviction_l3',
        'mooney_lab',
        'jlewis_lab',
        'capasso_lab',
        'mclaughlin_lab',
        'trible_lab',
        'seas_computing',
        'seas_iacs',
        'mloncar_lab',
        'doshi-velez_lab',
        'parker_lab',
        'mazur_lab_seas',
        'henrich_lab',
        'konkle_lab',
        'aldy_climate_l3',
        'dobbie_policetv_l3',
        'epod_alg884a_l3',
        'epod_dap320_l3',
        'epod_galanazi_l3',
        'epod_ksa_l3',
        'epod_sstemper_l3',
        'epod_zali_l3',
        'hausmann_albania_l3',
        'hausmann_albaniavat_l3',
        'hausmann_colombia_amazonia_l3',
        'hausmann_dynagaps_l3',
        'hausmann_ethiopia_l3',
        'hausmann_jordan_l3',
        'hausmann_kaz_l3',
        'hausmann_lka_l3',
        'hausmann_mastercard_l3',
        'hausmann_namibia_l3',
        'hausmann_saudi_l3',
        'hu_lab_seas',
        'koretz_team_l3',
        'kreindler_subsidized_transit_l3',
        'kubzansky_jhs_l3',
        'legewie_lab',
        'magnetometer_lise',
        'mcconnell_ctc_preg_l3',
        'mucci_hpfs_sequencing_l3',
        'nzipser_q_projects_l3',
        'pop_connectworks_l3',
        'pop_haalsi_internal_l3',
        'pop_haalsi_l3',
        'pop_mpxnyc_l3',
        'pop_regards_l3',
        'pop_vitalstatistics_l3',
        'praffler_duarte_customs_l3',
        'price_ukbiobank_l3',
        'zhang_lab',
        'jacob_lab',
        'stubbs_lab',
        'keith_lab_seas',
        'parkes_lab',
        'glaeser_schls_l3',
        'pfister_lab',
        'weitz_lab',
        'mahadevan_lab',
        'aziz_lab',
        'yacoby_lab',
        'howe_lab_seas',
        'wood_lab',
        'messerlian_lab',
        'dominici_nsaph',
        'aizenberg_lab',
        'martin_lab_seas',
        'smith_lab',
        'friend_lab',
        'jshapiro_lab',
        'vlassak_lab',
        'clarke_lab',
        'li_lab_seas',
        'ba_lab',
        'walsh_lab_seas',
        'fdoyle_lab',
        'mcelroy_lab',
        'nagpal_lab',
        'haneuse_ehr_l3',
        'pop_risk_l3',
        'pop_hrs_l3',
        'pop_eurostat_l3',
        'mckinney_lab',
        'pop_gallup_l3',
        'glaeser_cws_l3',
        'shepard_snaphealth_l3',
        'richardlee_lab',
        'nrg',
    ],
    'bos-isilon/tier1': [
        'giribet_lab',
        'huybers_lab',
        'huttenhower_lab',
        'michor_lab',
        'rush_lab',
        'ham_lab',
        'nelson_lab',
        'murphy_lab',
        'calmon_lab',
        'chetty_lab',
        'dominici_lab',
        'dvorkin_lab',
        'economics',
        'extavour_lab',
        'gershman_lab',
        'girguis_lab',
        'hsu_lab',
        'idreos_lab',
        'janson_lab',
        'jjohnson_lab',
        'kahne_lab',
        'koenig_lab',
        'lshaw_lab',
        'lu_lab',
        'manuelian_lab',
        'melton_users',
        'miller_lab',
        'mmurray_lab',
        'parmigiani_lab',
        'pierce_lab',
        'robins_lab',
        'russo_lab',
        'seage_lab',
        'shair_lab',
        'singer_lab',
        'sunderland_lab',
        'wagers_lab',
        'whipple_lab',
        'whitesides_lab',
        'woo_lab',
        'wordsworth_lab',
        'chsi_museum',
        'rubin_users',
        'spierce_lab',
        'chetty_covid',
        'gordon_lab',
        'hensch_users',
        'hepl',
        'hpnh',
        'israeli_hbs_lab',
        'junliu_lab',
        'mrimgmt',
        'murthy_users',
        'trauger_lab',
        'zheng_lab',
        'prigozhin_lab',
        'lds',
        'nrg',
        'pfister_lab',
        'g_smms_data',
        'microchem_users',
        'sequencing',
        'balskus_lab',
        'semitic_museum',
        'cgrdepartment',
        'g_nwl_core_admins',
        'nowak',
        'geology_museum',
        'tps_rc_poc',
        'arlotta_lab',
    ],
}

def march_2023_dr():
    '''
    Set billing code to unallowable for projects with holy and bos isilon allocations in 3/2023
    due to failure of the disaster recovery system.

    Billing should have already been run; this replaces the codes with the RC unallowable from science operations
    '''
    rc_unallowable_acct = Account.objects.get(name='RC Storage Unallowable', organization__name='Science Operations')

    year = 2023
    month = 3
    brs_to_adjust = []
    for product_name, project_list in PROJECTS.items():
        for project_name in project_list:
            for po in ProjectOrganization.objects.filter(project__title=project_name):
                brs_to_adjust.extend(list(BillingRecord.objects.filter(product_usage__product__product_name=product_name, account__organization=po.organization)))

    print(f'Found {len(brs_to_adjust)} brs')

    for br in brs_to_adjust:
        print(br)
        br.account = rc_unallowable_acct
        br.save()

    print('Done')
